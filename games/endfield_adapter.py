import requests
import hashlib
import hmac
import time
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EndfieldAdapter:
    """Adapter for Arknights: Endfield SKPort API"""

    BASE_URL = "https://zonai.skport.com/web/v1"
    OAUTH_URL = "https://as.gryphline.com"

    def __init__(self, account_token: str):
        """
        Initialize with SKPort account token or cred

        Args:
            account_token: OAuth token (JWT starting with eyJ) OR cred value (short token like skC2hd...)
        """
        self.account_token = account_token
        self.cred = None
        self.salt = None
        self.user_id = None
        self.session = requests.Session()

        # Check if this is a cred value (not a JWT token)
        # Cred values are short (30-50 chars) and don't start with 'eyJ'
        if not account_token.startswith('eyJ') and len(account_token) < 100:
            logger.info("Using provided cred value directly (legacy mode)")
            self.cred = account_token
            # In legacy mode, we don't have salt, so can only use v1 signatures

    def _perform_oauth_flow(self) -> bool:
        """
        Perform OAuth flow to get cred and salt for signing

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Step 1: Get basic info
            basic_url = f"{self.OAUTH_URL}/user/info/v1/basic?token={self.account_token}"
            basic_response = self.session.get(
                basic_url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            basic_data = basic_response.json()

            if basic_data.get("status") != 0:
                logger.error(f"OAuth Step 1 failed: {basic_data.get('msg', 'Unknown error')}")
                return False

            # Step 2: Grant OAuth code
            grant_response = self.session.post(
                f"{self.OAUTH_URL}/user/oauth2/v2/grant",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "token": self.account_token,
                    "appCode": "6eb76d4e13aa36e6",
                    "type": 0
                }
            )
            grant_data = grant_response.json()

            if grant_data.get("status") != 0 or not grant_data.get("data", {}).get("code"):
                logger.error(f"OAuth Step 2 failed: {grant_data.get('msg', 'Unknown error')}")
                return False

            code = grant_data["data"]["code"]

            # Step 3: Generate credentials
            cred_response = self.session.post(
                f"{self.BASE_URL}/user/auth/generate_cred_by_code",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "platform": "3",
                    "Referer": "https://www.skport.com/",
                    "Origin": "https://www.skport.com"
                },
                json={"code": code, "kind": 1}
            )
            cred_data = cred_response.json()

            if cred_data.get("code") != 0 or not cred_data.get("data", {}).get("cred"):
                logger.error(f"OAuth Step 3 failed: {cred_data.get('message', 'Unknown error')}")
                return False

            # Store credentials
            self.cred = cred_data["data"]["cred"]
            self.salt = cred_data["data"]["token"]
            self.user_id = cred_data["data"]["userId"]

            logger.info("OAuth flow successful")
            return True

        except Exception as e:
            logger.error(f"OAuth flow error: {e}")
            return False

    def _generate_sign_v1(self, timestamp: str) -> str:
        """
        Generate v1 signature (MD5 of "timestamp=X&cred=Y")

        Args:
            timestamp: Unix timestamp as string

        Returns:
            str: MD5 hash signature
        """
        sign_string = f"timestamp={timestamp}&cred={self.cred}"
        return hashlib.md5(sign_string.encode()).hexdigest()

    def _generate_sign_v2(self, path: str, timestamp: str) -> str:
        """
        Generate v2 signature (HMAC-SHA256 + MD5)
        Used for attendance endpoints

        Args:
            path: API endpoint path
            timestamp: Unix timestamp as string

        Returns:
            str: MD5 of HMAC-SHA256 signature
        """
        platform = "3"
        vname = "1.0.0"

        # Create header JSON
        header_json = json.dumps({
            "platform": platform,
            "timestamp": timestamp,
            "dId": "",
            "vName": vname
        }, separators=(',', ':'))  # No spaces in JSON

        # Create signing string
        sign_string = f"{path}{timestamp}{header_json}"

        # HMAC-SHA256 with salt
        hmac_hash = hmac.new(
            self.salt.encode(),
            sign_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # MD5 of HMAC result
        return hashlib.md5(hmac_hash.encode()).hexdigest()

    def _get_headers(self, path: str = None, use_v2_sign: bool = False) -> Dict[str, str]:
        """
        Generate headers with signature

        Args:
            path: API endpoint path (required for v2 signature)
            use_v2_sign: Whether to use v2 signature

        Returns:
            Dict: Headers dictionary
        """
        timestamp = str(int(time.time()))

        headers = {
            "User-Agent": "Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31;) Okhttp/4.11.0",
            "Accept-Encoding": "gzip",
            "Connection": "close",
            "platform": "3",
            "timestamp": timestamp,
            "dId": "",
            "vName": "1.0.0",
            "cred": self.cred
        }

        # Only use v2 signature if we have salt (from OAuth flow)
        if use_v2_sign and path and self.salt:
            headers["sign"] = self._generate_sign_v2(path, timestamp)
        else:
            headers["sign"] = self._generate_sign_v1(timestamp)

        return headers

    def check_attendance(self) -> Dict[str, Any]:
        """
        Check attendance status (GET)

        Returns:
            {
                "success": bool,
                "message": str,
                "data": {
                    "hasToday": bool,
                    "calendar": [...],
                    "resourceInfoMap": {...}
                }
            }
        """
        try:
            # Ensure we have credentials
            if not self.cred:
                # Try OAuth flow if we have an account_token
                if self.account_token and not self._perform_oauth_flow():
                    return {
                        "success": False,
                        "message": "OAuth authentication failed"
                    }

            url = f"{self.BASE_URL}/game/endfield/attendance"
            headers = self._get_headers()

            logger.debug(f"GET {url}")
            logger.debug(f"Headers: {headers}")

            response = self.session.get(url, headers=headers)
            result = response.json()

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response body: {json.dumps(result, indent=2)}")

            if result.get("code") == 0:
                return {
                    "success": True,
                    "message": result.get("msg", "OK"),
                    "data": result.get("data", {})
                }
            else:
                return {
                    "success": False,
                    "message": result.get("msg", "Unknown error"),
                    "data": {}
                }

        except Exception as e:
            logger.error(f"Check attendance error: {e}")
            return {
                "success": False,
                "message": str(e),
                "data": {}
            }

    def claim_attendance(self) -> Dict[str, Any]:
        """
        Claim attendance reward (POST with v2 signature)

        Returns:
            {
                "success": bool,
                "message": str,
                "data": {
                    "awardIds": [...],
                    "resourceInfoMap": {...}
                }
            }
        """
        try:
            # Ensure we have credentials with salt for v2 signature
            if not self.cred:
                # Try OAuth flow if we have an account_token
                if self.account_token and not self._perform_oauth_flow():
                    return {
                        "success": False,
                        "message": "OAuth authentication failed"
                    }

            # CRITICAL: If we have cred but no salt, we MUST get it via OAuth
            # The claim POST requires v2 signature which needs salt
            if not self.salt and self.account_token and not self.account_token.startswith('eyJ'):
                logger.error("⚠️  CRITICAL: Cred-only mode cannot use v2 signature for claim!")
                logger.error("    The claim POST endpoint requires v2 signature with salt.")
                logger.error("    Please use account_token (JWT) instead of cred for Endfield.")
                return {
                    "success": False,
                    "message": "Cred-only mode not supported for claim. Need account_token (JWT)."
                }

            url = f"{self.BASE_URL}/game/endfield/attendance"
            sign_path = "/web/v1/game/endfield/attendance"
            headers = self._get_headers(path=sign_path, use_v2_sign=True)

            logger.debug(f"POST {url}")
            logger.debug(f"Sign path: {sign_path}")
            logger.debug(f"Using v2 signature: {self.salt is not None}")
            logger.debug(f"Headers: {headers}")

            response = self.session.post(url, headers=headers)
            result = response.json()

            logger.info(f"✓ Claim response status: {response.status_code}")
            logger.info(f"✓ Claim response body: {json.dumps(result, indent=2)}")

            if result.get("code") == 0:
                return {
                    "success": True,
                    "message": result.get("msg", "OK"),
                    "data": result.get("data", {})
                }
            else:
                logger.error(f"❌ Claim failed with code {result.get('code')}: {result.get('msg', 'Unknown error')}")
                return {
                    "success": False,
                    "message": result.get("msg", "Unknown error"),
                    "data": {}
                }

        except Exception as e:
            logger.error(f"Claim attendance error: {e}")
            return {
                "success": False,
                "message": str(e),
                "data": {}
            }

    def perform_checkin(self) -> Dict[str, Any]:
        """
        Complete check-in flow (check status then claim if needed)

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
            # Check current status
            logger.info("Checking Endfield attendance status...")
            status = self.check_attendance()

            if not status["success"]:
                return {
                    "success": False,
                    "message": status["message"],
                    "already_signed": False,
                    "reward": None,
                    "total_sign_day": 0
                }

            # Check if already signed today
            has_today = status["data"].get("hasToday", False)
            calendar = status["data"].get("calendar", [])
            resource_map = status["data"].get("resourceInfoMap", {})

            # Count total signed days
            total_signed = len([c for c in calendar if c.get("done", False)])

            if has_today:
                # Get the reward that was claimed today
                last_done = None
                for record in calendar:
                    if record.get("done"):
                        last_done = record

                reward_info = None
                if last_done:
                    award_id = last_done.get("awardId")
                    if award_id and award_id in resource_map:
                        resource = resource_map[award_id]
                        reward_info = {
                            "name": resource.get("name", "Unknown"),
                            "count": resource.get("count", 0),
                            "icon": resource.get("icon", "")
                        }

                logger.info("Already signed in today")
                return {
                    "success": True,
                    "message": "Already checked in today",
                    "already_signed": True,
                    "reward": reward_info,
                    "total_sign_day": total_signed
                }

            # Get today's reward from calendar (first not done)
            next_reward_info = None
            for day in calendar:
                if not day.get("done"):
                    award_id = day.get("awardId")
                    if award_id and award_id in resource_map:
                        resource = resource_map[award_id]
                        next_reward_info = {
                            "name": resource.get("name", "Unknown"),
                            "count": resource.get("count", 0),
                            "icon": resource.get("icon", "")
                        }
                    break

            # Claim attendance
            logger.info("Claiming Endfield attendance...")
            claim = self.claim_attendance()

            if claim["success"]:
                # Parse rewards from claim response
                award_ids = claim["data"].get("awardIds", [])
                claim_resource_map = claim["data"].get("resourceInfoMap", {})

                rewards = []
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

                # Use claim response if available, otherwise use calendar prediction
                primary_reward = rewards[0] if rewards else next_reward_info

                if rewards:
                    reward_text = ", ".join([f"{r['name']} x{r['count']}" for r in rewards])
                elif primary_reward:
                    reward_text = f"{primary_reward['name']} x{primary_reward['count']}"
                else:
                    reward_text = "Unknown reward"

                logger.info(f"Attendance claimed successfully! Rewards: {reward_text}")

                return {
                    "success": True,
                    "message": f"Attendance claimed! Received: {reward_text}",
                    "already_signed": False,
                    "reward": primary_reward,
                    "total_sign_day": total_signed + 1
                }
            else:
                return {
                    "success": False,
                    "message": claim["message"],
                    "already_signed": False,
                    "reward": None,
                    "total_sign_day": total_signed
                }

        except Exception as e:
            logger.error(f"Endfield check-in error: {e}")
            return {
                "success": False,
                "message": str(e),
                "already_signed": False,
                "reward": None,
                "total_sign_day": 0
            }
