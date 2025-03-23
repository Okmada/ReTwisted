from macro.twistedmacro.twistedmacro_latest import TwistedMacro_latest

Macros = {m.__name__: m for m in [
    TwistedMacro_latest,
]}

DefaultMacro = TwistedMacro_latest.__name__