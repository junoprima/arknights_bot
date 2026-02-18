import requests
import hashlib
import hmac
import time
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EndfieldAdapter:
    """
    Adapter for Arknights: Endfield SKPort API

    Based on the correct flow from:
    - https://github.com/Areha11Fz/ArknightsEndfieldAutoCheckIn
    - https://github.com/torikushiii/endfield-auto

    Flow:
    1. ACCOUNT_TOKEN → OAuth code
    2. OAuth code → cred
    3. cred → sign_token (from /auth/refresh)
    4. sign_token → used in HMAC signatures
    """

    BASE_URL = "https://zonai.skport.com/web/v1"
    API_BASE_URL = "https://zonai.skport.com/api/v1"
    OAUTH_URL = "https://as.gryphline.com"

    APP_CODE = "6eb76d4e13aa36e6"
    PLATFORM = "3"
    VNAME = "1.0.0"
    ENDFIELD_GAME_ID = "3"

    def __init__(self, account_token: str, account_name: str = "Unknown"):
        """
        Initialize with SKPort ACCOUNT_TOKEN (from browser cookies)
        OR with cred value directly (if you already have it)

        Args:
            account_token: ACCOUNT_TOKEN cookie OR cred value
            account_name: Name of the account for logging
        """
        self.account_token = account_token
        self.account_name = account_name
        self.cred = None
        self.sign_token = None
        self.game_role = None
        self.session = requests.Session()

        # Check if this is a cred value (short token)
        if not account_token.startswith('eyJ') and len(account_token) < 100:
            logger.info("Using provided cred value directly")
            self.cred = account_token

    def _get_oauth_code(self) -> Optional[str]:
        """
        Step 1: Get OAuth code from ACCOUNT_TOKEN

        Returns:
            OAuth code string or None
        """
        try:
            url = f"{self.OAUTH_URL}/user/oauth2/v2/grant"
            payload = {
                "token": self.account_token,
                "appCode": self.APP_CODE,
                "type": 0
            }

            response = self.session.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )

            data = response.json()

            if data.get("status") == 0 and data.get("data", {}).get("code"):
                logger.info("✓ OAuth code obtained")
                return data["data"]["code"]
            else:
                logger.error(f"Failed to get OAuth code: {data.get('msg', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"Error getting OAuth code: {e}")
            return None

    def _get_cred(self, oauth_code: str) -> Optional[str]:
        """
        Step 2: Get cred from OAuth code

        Args:
            oauth_code: OAuth code from step 1

        Returns:
            cred string or None
        """
        try:
            url = f"{self.BASE_URL}/user/auth/generate_cred_by_code"
            payload = {
                "kind": 1,
                "code": oauth_code
            }

            response = self.session.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "platform": self.PLATFORM,
                    "Referer": "https://www.skport.com/",
                    "Origin": "https://www.skport.com"
                }
            )

            data = response.json()

            if data.get("code") == 0 and data.get("data", {}).get("cred"):
                cred = data["data"]["cred"]
                logger.info(f"✓ Cred obtained: {cred[:10]}...")
                return cred
            else:
                logger.error(f"Failed to get cred: {data.get('message', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"Error getting cred: {e}")
            return None

    def _get_sign_token(self) -> Optional[str]:
        """
        Step 3: Get sign_token from cred (via /auth/refresh)

        This is the KEY step that was missing!
        The sign_token is used in HMAC signatures.

        Returns:
            sign_token string or None
        """
        try:
            url = f"{self.BASE_URL}/auth/refresh"
            timestamp = str(int(time.time()))

            headers = {
                "cred": self.cred,
                "platform": self.PLATFORM,
                "vname": self.VNAME,
                "timestamp": timestamp,
                "sk-language": "en"
            }

            response = self.session.get(url, headers=headers)
            data = response.json()

            if data.get("code") == 0 and data.get("data", {}).get("token"):
                sign_token = data["data"]["token"]
                logger.info(f"✓ Sign token obtained: {sign_token[:10]}...")
                return sign_token
            else:
                logger.error(f"Failed to get sign token: {data.get('message', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"Error getting sign token: {e}")
            return None

    def _get_player_binding(self) -> Optional[str]:
        """
        Step 4: Get player game role binding

        Returns:
            game_role string (format: "3_roleId_serverId") or None
        """
        try:
            url = f"{self.API_BASE_URL}/game/player/binding"
            timestamp = str(int(time.time()))
            path = "/api/v1/game/player/binding"

            # Compute signature
            signature = self._compute_sign(path, "", timestamp)

            headers = {
                "cred": self.cred,
                "platform": self.PLATFORM,
                "vname": self.VNAME,
                "timestamp": timestamp,
                "sk-language": "en",
                "sign": signature
            }

            response = self.session.get(url, headers=headers)
            data = response.json()

            if data.get("code") == 0 and data.get("data", {}).get("list"):
                apps = data["data"]["list"]
                for app in apps:
                    if app.get("appCode") == "endfield" and app.get("bindingList"):
                        binding = app["bindingList"][0]
                        role = binding.get("defaultRole") or (binding.get("roles", [{}])[0] if binding.get("roles") else None)
                        if role:
                            role_id = role.get("roleId")
                            server_id = role.get("serverId")
                            game_role = f"{self.ENDFIELD_GAME_ID}_{role_id}_{server_id}"
                            logger.info(f"✓ Game role obtained: {game_role}")
                            return game_role

            logger.warning(f"No Endfield binding found for account: {self.account_name}")
            return None

        except Exception as e:
            logger.error(f"Error getting player binding: {e}")
            return None

    def _compute_sign(self, path: str, body: str, timestamp: str) -> str:
        """
        Compute HMAC-SHA256 + MD5 signature

        This is the v2 signature used for API calls.
        Uses sign_token (not salt!) as the HMAC key.

        Args:
            path: API endpoint path
            body: Request body (empty for GET)
            timestamp: Unix timestamp

        Returns:
            MD5 hex string
        """
        header_obj = {
            "platform": self.PLATFORM,
            "timestamp": timestamp,
            "dId": "",
            "vName": self.VNAME
        }

        # JSON with no spaces
        headers_json = json.dumps(header_obj, separators=(',', ':'))

        # Sign string: path + body + timestamp + headers
        sign_string = f"{path}{body}{timestamp}{headers_json}"

        # HMAC-SHA256 with sign_token as key
        hmac_hash = hmac.new(
            self.sign_token.encode(),
            sign_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # MD5 of HMAC result
        md5_hash = hashlib.md5(hmac_hash.encode()).hexdigest()

        return md5_hash

    def authenticate(self) -> bool:
        """
        Complete authentication flow

        Returns:
            True if successful, False otherwise
        """
        try:
            # If cred not provided, get it via OAuth
            if not self.cred:
                logger.info("Starting OAuth flow...")

                oauth_code = self._get_oauth_code()
                if not oauth_code:
                    return False

                cred = self._get_cred(oauth_code)
                if not cred:
                    return False

                self.cred = cred

            # Get sign token (CRITICAL STEP!)
            sign_token = self._get_sign_token()
            if not sign_token:
                return False

            self.sign_token = sign_token

            # Get player binding (optional but recommended)
            game_role = self._get_player_binding()
            self.game_role = game_role

            logger.info("✅ Authentication complete!")
            return True

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def check_attendance(self) -> Dict[str, Any]:
        """
        Check attendance status

        Returns:
            Response dict with attendance data
        """
        try:
            url = f"{self.BASE_URL}/game/endfield/attendance"
            timestamp = str(int(time.time()))
            path = "/web/v1/game/endfield/attendance"

            # Compute signature
            signature = self._compute_sign(path, "", timestamp)

            headers = {
                "cred": self.cred,
                "platform": self.PLATFORM,
                "vname": self.VNAME,
                "timestamp": timestamp,
                "sk-language": "en",
                "sign": signature
            }

            if self.game_role:
                headers["sk-game-role"] = self.game_role

            response = self.session.get(url, headers=headers)
            data = response.json()

            logger.debug(f"Check attendance response: {json.dumps(data, indent=2)}")

            return data

        except Exception as e:
            logger.error(f"Check attendance error: {e}")
            return {"code": -1, "message": str(e)}

    def claim_attendance(self) -> Dict[str, Any]:
        """
        Claim attendance reward

        Returns:
            Response dict with claim result
        """
        try:
            url = f"{self.BASE_URL}/game/endfield/attendance"
            timestamp = str(int(time.time()))
            path = "/web/v1/game/endfield/attendance"

            # Compute signature (with empty body for POST)
            signature = self._compute_sign(path, "", timestamp)

            headers = {
                "cred": self.cred,
                "platform": self.PLATFORM,
                "vname": self.VNAME,
                "timestamp": timestamp,
                "sk-language": "en",
                "sign": signature,
                "Content-Type": "application/json"
            }

            if self.game_role:
                headers["sk-game-role"] = self.game_role

            logger.info(f"Claiming attendance...")
            logger.debug(f"Headers: {headers}")

            response = self.session.post(url, headers=headers)
            data = response.json()

            logger.info(f"✓ Claim response: {json.dumps(data, indent=2)}")

            return data

        except Exception as e:
            logger.error(f"Claim attendance error: {e}")
            return {"code": -1, "message": str(e)}

    def perform_checkin(self) -> Dict[str, Any]:
        """
        Complete check-in flow

        Returns:
            {
                "success": bool,
                "message": str,
                "already_signed": bool,
                "reward": Optional[Dict],
                "total_sign_day": int
            }
        """
        try:
            # Authenticate
            if not self.authenticate():
                return {
                    "success": False,
                    "message": "Authentication failed",
                    "already_signed": False,
                    "reward": None,
                    "total_sign_day": 0
                }

            # Check current status
            check_data = self.check_attendance()

            if check_data.get("code") != 0:
                return {
                    "success": False,
                    "message": check_data.get("message", "Failed to check attendance"),
                    "already_signed": False,
                    "reward": None,
                    "total_sign_day": 0
                }

            # Check if already signed
            has_today = check_data.get("data", {}).get("hasToday", False)
            calendar = check_data.get("data", {}).get("calendar", [])
            resource_map = check_data.get("data", {}).get("resourceInfoMap", {})

            total_signed = len([c for c in calendar if c.get("done", False)])

            if has_today:
                # Already signed in today
                last_reward = None
                for record in calendar:
                    if record.get("done"):
                        award_id = record.get("awardId")
                        if award_id and award_id in resource_map:
                            resource = resource_map[award_id]
                            last_reward = {
                                "name": resource.get("name", "Unknown"),
                                "count": resource.get("count", 0),
                                "icon": resource.get("icon", "")
                            }

                return {
                    "success": True,
                    "message": "Already signed in today",
                    "already_signed": True,
                    "reward": last_reward,
                    "total_sign_day": total_signed
                }

            # Claim attendance
            claim_data = self.claim_attendance()

            # Check claim result
            code = claim_data.get("code")
            msg = claim_data.get("message", "")

            # Success (code 0)
            if code == 0:
                # Parse rewards
                rewards = []
                award_ids = claim_data.get("data", {}).get("awardIds", [])
                claim_resource_map = claim_data.get("data", {}).get("resourceInfoMap", {})

                if award_ids and claim_resource_map:
                    for award in award_ids:
                        award_id = award.get("id") if isinstance(award, dict) else award
                        if award_id and award_id in claim_resource_map:
                            resource = claim_resource_map[award_id]
                            rewards.append({
                                "name": resource.get("name", "Unknown"),
                                "count": resource.get("count", 0),
                                "icon": resource.get("icon", "")
                            })

                primary_reward = rewards[0] if rewards else None
                reward_text = ", ".join([f"{r['name']} x{r['count']}" for r in rewards]) if rewards else "Unknown"

                logger.info(f"✅ Attendance claimed! Rewards: {reward_text}")

                return {
                    "success": True,
                    "message": f"Signed in successfully! Rewards: {reward_text}",
                    "already_signed": False,
                    "reward": primary_reward,
                    "total_sign_day": total_signed + 1
                }

            # Already signed in (code 1001 or 10001)
            elif code in [1001, 10001] or "already" in msg.lower():
                return {
                    "success": True,
                    "message": "Already signed in today",
                    "already_signed": True,
                    "reward": None,
                    "total_sign_day": total_signed
                }

            # Token expired (code 10002)
            elif code == 10002:
                return {
                    "success": False,
                    "message": "Account token expired. Please update your token.",
                    "already_signed": False,
                    "reward": None,
                    "total_sign_day": 0
                }

            # Other error
            else:
                return {
                    "success": False,
                    "message": f"API Error (code {code}): {msg}",
                    "already_signed": False,
                    "reward": None,
                    "total_sign_day": total_signed
                }

        except Exception as e:
            logger.error(f"Check-in error: {e}")
            return {
                "success": False,
                "message": str(e),
                "already_signed": False,
                "reward": None,
                "total_sign_day": 0
            }
