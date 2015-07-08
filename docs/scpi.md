

    SCPI = SCPI_COMMAND | SCPI_GET | SCPI_SET
    SCPI_COMMAND = KEYWORD[:SCPI_COMMAND]
    SCPI_GET = SCPI_COMMAND?
    SCPI_PUT = SCPI_COMMAND PARAMS
    KEYWORD = (A-Z)+(a-z)*
    PARAMS = PARAM[,PARAM]+
    PARAM = (A-Z|a-z|0-9| )+

Examples:

    CALibration:BEGin
    SYSTem:HELP?
    FREQuency:CW 200000

Uppercase and lowercase parts of the chunk are only used for documenting
available commands, in fact they might be all lowercase, uppsercase or mixed.

Uppercase part of the chunk is mandatory, and has to present in the command.
Lowercase is optional and only serves readability. However, if it present in
a command, it has to be printed i.e. SYSTe:HELP? will be an invalid command.

IEEE mandated SCPI commands start with asterisk, e.g. *IDN?, *RST, *WAI
These are commands mandatory for implementation by SCPI-compatible devices
