"""Speech output adapter."""

import logging
import shutil
import subprocess

import config

logger = logging.getLogger(__name__)
SPEECH_STATUS = "Not tested" if config.SPEECH_ENABLED else "Disabled"


def speak(text):
    """Speak text, logging speech engine failures without interrupting commands."""
    global SPEECH_STATUS
    if not config.SPEECH_ENABLED:
        SPEECH_STATUS = "Disabled"
        return
    executable = shutil.which(config.SPEECH_ENGINE)
    if executable is None:
        SPEECH_STATUS = "Unavailable"
        logger.error("Speech output executable %r was not found", config.SPEECH_ENGINE)
        return
    try:
        subprocess.run(
            [
                executable,
                "-s", str(config.SPEECH_RATE),
                "-a", str(round(max(0, min(1, config.SPEECH_VOLUME)) * 200)),
                "--",
                str(text),
            ],
            check=True,
        )
        SPEECH_STATUS = "Ready"
    except (OSError, subprocess.CalledProcessError):
        SPEECH_STATUS = "Unavailable"
        logger.exception("Speech output failed")
