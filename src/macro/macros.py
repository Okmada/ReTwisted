from macro.helicitymacro.helicitymacro import HelicityMacro
from macro.twistedmacro.twistedmacro_1_19_1 import TwistedMacro_1_19_1
from macro.twistedmacro.twistedmacro_latest import TwistedMacro_latest
from macro.twistedmacro.twistedmacro_event import TwistedMacro_event

Macros = {m.__name__: m for m in [
    TwistedMacro_latest,
    TwistedMacro_event,
    TwistedMacro_1_19_1,
    HelicityMacro,
]}

DefaultMacro = TwistedMacro_latest.__name__