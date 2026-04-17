from __future__ import annotations


class AsrEvalError(Exception):
    """Base class for asr-eval-lib exceptions."""


class ProfileError(AsrEvalError):
    """Raised when a profile or metric combination is unsupported."""


class TranscriptError(AsrEvalError):
    """Raised when reference and hypothesis inputs cannot be matched."""


class SctkNotFoundError(AsrEvalError):
    """Raised when a required SCTK executable is missing."""


class SctkExecutionError(AsrEvalError):
    """Raised when an SCTK command exits unsuccessfully."""

    def __init__(self, command, returncode, stdout="", stderr=""):
        self.command = tuple(str(part) for part in command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            "SCTK command failed with exit code {0}: {1}\n{2}".format(
                returncode,
                " ".join(self.command),
                stderr.strip() or stdout.strip(),
            )
        )
