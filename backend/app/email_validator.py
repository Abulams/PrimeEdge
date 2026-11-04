"""
Email verification utilities for PrimeEdge.
- Blocks disposable and temporary email domains.
- Verifies domain DNS MX records to prevent non-existent / fake domains.
"""
import re
import socket
import logging
from typing import Tuple

logger = logging.getLogger("marketos.email_validator")

# Comprehensive list of disposable, temporary, and throwaway email domains
DISPOSABLE_DOMAINS = {
    # Popular disposable services
    "mailinator.com", "yopmail.com", "guerrillamail.com", "guerrillamailblock.com",
    "sharklasers.com", "grr.la", "guerrillamail.biz", "guerrillamail.de",
    "guerrillamail.net", "guerrillamail.org", "10minutemail.com", "10minutemail.net",
    "tempmail.com", "temp-mail.org", "trashmail.com", "trashmail.net",
    "dispostable.com", "getairmail.com", "fakeinbox.com", "maildrop.cc",
    "inboxbear.com", "tempail.com", "throwawaymail.com", "generator.email",
    "mohmal.com", "burnermail.io", "crazymailing.com", "nada.ltd",
    "getnada.com", "abyssmail.com", "dropmail.me", "fakemailgenerator.com",
    "emailondeck.com", "tempinbox.com", "mytemp.email", "luxusmail.org",
    "minutemailbox.com", "tmail.ws", "tempmailo.com", "tmpmail.net",
    "tmpmail.org", "bupmail.com", "byom.de", "dayrep.com", "teleworm.us",
    "superrito.com", "rhyta.com", "armyspy.com", "cuvox.de", "fleckens.hu",
    "einrot.com", "jourrapide.com", "gustr.com",
}

# Domains known to be invalid/test
INVALID_DOMAINS = {
    "test.com", "example.com", "example.org", "example.net",
    "fake.com", "asdf.com", "none.com", "noemail.com", "invalid.com"
}


def validate_email_authenticity(email: str) -> Tuple[bool, str]:
    """
    Validates email format, checks against disposable email providers,
    and checks if the domain exists and accepts email (MX / DNS records).

    Returns:
        (is_valid: bool, error_message: str)
    """
    if not email or "@" not in email:
        return False, "Invalid email address format."

    clean_email = email.strip().lower()
    parts = clean_email.split("@")
    if len(parts) != 2:
        return False, "Invalid email address format."

    local_part, domain = parts[0], parts[1]

    # 1. Basic syntax checks
    if len(local_part) < 1 or len(domain) < 4 or "." not in domain:
        return False, "Invalid email address format."

    # 2. Check disposable & blocked domains
    if domain in DISPOSABLE_DOMAINS or domain in INVALID_DOMAINS:
        logger.warning(f"Rejected registration with disposable email domain: {domain}")
        return False, "Disposable or temporary email addresses are not permitted. Please use a valid personal or business email."

    # Also check if domain ends with disposable suffix
    for disp in DISPOSABLE_DOMAINS:
        if domain.endswith("." + disp):
            return False, "Disposable or temporary email addresses are not permitted."

    # 3. DNS / MX Record Verification
    # Try dnspython first for true MX records, fallback to socket DNS resolution
    try:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(domain, "MX", lifetime=3.0)
            if not answers:
                return False, f"The domain '@{domain}' cannot receive emails (no MX records found)."
            return True, ""
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            # No MX record; try A record fallback
            try:
                dns.resolver.resolve(domain, "A", lifetime=3.0)
                return True, ""
            except Exception:
                return False, f"The domain '@{domain}' does not exist or cannot receive mail."
        except dns.resolver.Timeout:
            # DNS timeout - allow through rather than blocking legit users on slow DNS
            logger.warning(f"DNS timeout verifying domain {domain}, permitting.")
            return True, ""
        except Exception as e:
            logger.warning(f"DNS resolver warning for {domain}: {e}")
            # Fallback to socket check below
    except ImportError:
        pass

    # Socket resolution fallback: Verify domain IP exists
    try:
        socket.gethostbyname(domain)
        return True, ""
    except socket.gaierror:
        return False, f"The domain '@{domain}' does not exist. Please check your email spelling."
    except Exception as e:
        logger.warning(f"Socket resolution error for {domain}: {e}")
        return True, ""
