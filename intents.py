import re

def detect_intent(text: str) -> str:
    t = text.lower().strip()

    # status / missing docs
    if any(k in t for k in ["missing", "what am i missing", "what's missing", "remaining", "left to upload"]):
        return "MISSING_DOCS"

    if any(k in t for k in ["for each application", "each application", "all applications", "for every application"]):
            return "REQS_ALL_APPS"
    # list apps
    if any(k in t for k in ["my applications", "list applications", "show applications", "what did i apply"]):
        return "LIST_APPS"

    # delete
    if any(k in t for k in ["delete", "remove"]) and any(k in t for k in ["document", "file", "passport", "transcript", "cv"]):
        # if contains an explicit doc id like "#12" or "id 12"
        if re.search(r"(#|id\s*)(\d+)", t):
            return "DELETE_DOC_ID"
        if "all" in t:
            return "DELETE_ALL_DOCS"
        return "DELETE_DOC"

    # doc requirements general
    if any(k in t for k in ["documents required", "requirements", "what documents", "what do i need"]):
        return "REQUIREMENTS"

    return "GENERAL"

