import logging
from deep_translator import GoogleTranslator  # type: ignore

logger = logging.getLogger("translator")

# Supported translation languages (safe Latin character sets for ReportLab default fonts)
SUPPORTED_LANGUAGES = {
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese"
}

def translate_text(text: str, target_lang: str) -> str:
    """
    Translates input text to the target language using GoogleTranslator.
    Falls back to original text if target is 'en' or translation fails.
    """
    if not text:
        return ""
        
    target_lang = target_lang.lower().strip()
    if target_lang == "en" or target_lang not in SUPPORTED_LANGUAGES:
        return text
        
    try:
        logger.info(f"Translating text to {SUPPORTED_LANGUAGES[target_lang]} ({target_lang})...")
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return translated
    except Exception as e:
        logger.error(f"Translation to '{target_lang}' failed: {e}. Returning original text.")
        return text
