# s3270 Manual Page

## Contents

> [Name](#Name)<br>
> [Synopsis](#Synopsis)<br>
> [Description](#Description)<br>
> [Options](#Options)<br>
> [Character Sets](#Character-Sets)<br>
> [NVT Mode](#NVT-Mode)<br>
> [Toggles](#Toggles)<br>
> [Actions](#Actions)<br>
> [File Transfer](#File-Transfer)<br>
> [The PrintText Action](#The-PrintText-Action)<br>
> [Nested Scripts](#Nested-Scripts)<br>
> [Passthru](#Passthru)<br>
> [Proxy](#Proxy)<br>
> [Resources](#Resources)<br>
> [Files](#Files)<br>
> [See Also](#See-Also)<br>
> [Copyrights](#Copyrights)<br>
> [Version](#Version)

## Name

s3270 - IBM host access tool

## Synopsis

**s3270** [_options_] [_host_]<br>
**s3270** [_options_] _session-file_.s3270

## Description

**s3270** opens a telnet connection to an IBM host, then allows a script to control the host login session. It is derived from [_x3270_(1)](x3270-man.html), an X-windows IBM 3270 emulator. It implements RFCs 2355 (TN3270E), 1576 (TN3270) and 1646 (LU name selection), and supports IND$FILE file transfer. The full syntax for _host_ is:

> [_prefix_:]...[_LUname_@]_hostname_[:_port_]

Prepending a **P:** onto _hostname_ causes the connection to go through the _telnet-passthru_ service rather than directly to the host. See [PASSTHRU](#Passthru) below.

Prepending an **S:** onto _hostname_ removes the "extended data stream" option reported to the host. See [**-tn**](#tn) below for further information.

Prepending an **N:** onto _hostname_ turns off TN3270E support for the session.

Prepending an **L:** onto _hostname_ causes **s3270** to first create an SSL tunnel to the host, and then create a TN3270 session inside the tunnel. (This function is supported only if **s3270** was built with SSL/TLS support). Note that TLS-encrypted sessions using the TELNET START-TLS option are negotiated with the host automatically; for these sessions the **L:** prefix should not be used.

Prepending a **B:** onto _hostname_ changes the interaction of scripts and the host BIND-IMAGE message. Without **B:**, s3270 will unlock the keyboard as soon as a BIND-IMAGE is received. With **B:**, it will wait for a Write command that explicitly unlocks the keyboard.

A specific Logical Unit (LU) name to use may be specified by prepending it to the _hostname_ with an `**@**'. Multiple LU names to try can be separated by commas. An empty LU can be placed in the list with an extra comma. (Note that the LU name is used for different purposes by different kinds of hosts. For example, CICS uses the LU name as the Terminal ID.)

The _hostname_ may optionally be placed inside square-bracket characters `**[**' and `**]**'. This will prevent any colon `**:**' characters in the hostname from being interpreted as indicating option prefixes or port numbers. This allows numeric IPv6 addresses to be used as hostnames.

On systems that support the _forkpty_ library call, the _hostname_ may be replaced with **-e** and a command string. This will cause **s3270** to connect to a local child process, such as a shell.

The port to connect to defaults to **telnet**. This can be overridden with the **-port** option, or by appending a _port_ to the _hostname_ with a colon `**:**'. (For compatability with previous versions of **s3270** and with _tn3270_(1), the _port_ may also be specified as a second, separate argument.)

## Options

**s3270** understands the following options:

**-accepthostname** _spec_

Specifies a particular hostname to accept when validating the name presented in the host's SSL certificate, instead of comparing to the name or address used to make the connection. _spec_ can either be **any**, which disables name validation, **DNS:**_hostname_, which matches a particular DNS hostname, or **IP:**_address_, which matches a particular numeric IPv4 or IPv6 address.

**-cadir** _directory_

Specifies a directory containing CA (root) certificates to use when verifying a certificate provided by the host.

**-cafile** _filename_

Specifies a PEM-format file containing CA (root) certificates to use when verifying a certificate provided by the host.

**-certfile** _filename_

Specifies a file containing a certificate to provide to the host, if requested. The default file type is PEM.

**-certfiletype** _type_

Specifies the type of the certificate file specified by **-certfile**. _Type_ can be **pem** or **asn1**.

**-chainfile _filename_**

Specifies a certificate chain file in PEM format, containing a certificate to provide to the host if requested, as well as one or more intermediate certificates and the CA certificate used to sign that certificate. If **-chainfile** is specified, it overrides **-certfile**.

**-charset** _name_

Specifies an EBCDIC host character set. See [CHARACTER SETS](#Character-Sets) below.

**-clear** _toggle_

Sets the initial value of _toggle_ to **false**. The list of toggle names is under [TOGGLES](#Toggles) below.

**-devname** _name_

Specifies a device name (workstation ID) for RFC 4777 support.

**-httpd** **[**_addr_**:]**_port_

Specifies a port and optional address to listen on for HTTP connections. _Addr_ can be specified as `*' to indicate 0.0.0.0; the default is 127.0.0.1\. IPv6 numeric addresses must be specified inside of square brackets, e.g., [::1]:4080 to specify the IPv6 loopback address and TCP port 4080.

Note that this option is mutually-exclusive with the -scriptport option and disables reading commands from standard input.

**-keyfile** _filename_

Specifies a file containing the private key for the certificate file (specified via **-certfile** or **-chainfile**). The default file type is PEM.

**-keyfiletype** _type_

Specifies the type of the private key file specified by **-keyfile**. _Type_ can be **pem** or **asn1**.

**-keypasswd** _type_:_value_

Specifies the password for the private key file, if it is encrypted. The argument can be **file**:_filename_, specifying that the password is in a file, or **string**:_string_, specifying the password on the command-line directly. If the private key file is encrypted and no **-keypasswd** option is given, secure connections will not be allowed.

**-km** _name_

Specifies the local encoding method for multi-byte text. _name_ is an encoding name recognized by the ICU library. (Supported only when s3270 is compiled with DBCS support, and necessary only when s3270 cannot figure it out from the locale.)

**-loginmacro** _Action(arg...) ..._

Specifies a macro to run at login time.

**-model** _name_

The model of 3270 display to be emulated. The model name is in two parts, either of which may be omitted:

The first part is the **base model**, which is either **3278** or **3279**. **3278** specifies a monochrome (green on black) 3270 display; **3279** specifies a color 3270 display.

The second part is the **model number**, which specifies the number of rows and columns. Model 4 is the default.

Model Number

Columns

Rows

2

80

24

3

80

32

4

80

43

5

132

27

Note: Technically, there is no such 3270 display as a 3279-4 or 3279-5, but most hosts seem to work with them anyway.

The default model is **3279-4**.

**-nvt**

Start in NVT mode instead of waiting for the host to send data, and make the default terminal type **xterm**.

**-oversize** _cols_**x**_rows_

Makes the screen larger than the default for the chosen model number. This option has effect only in combination with extended data stream support (controlled by the "s3270.extended" resource), and only if the host supports the Query Reply structured field. The number of columns multiplied by the number of rows must not exceed 16383 (3fff hex), the limit of 14-bit 3270 buffer addressing.

**-port** _n_

Specifies a different TCP port to connect to. _n_ can be a name from **/etc/services** like **telnet**, or a number. This option changes the default port number used for all connections. (The positional parameter affects only the initial connection.)

**-proxy _type_:_host_[:_port_]**

Causes **s3270** to connect via the specified proxy, instead of using a direct connection. The _host_ can be an IP address or hostname. The optional _port_ can be a number or a service name. For a list of supported proxy _types_, see [PROXY](#Proxy) below.

**-scriptport** **[**_addr_**:]**_port_

Specifies a port and optional address to listen on for scripting connections. _Addr_ can be specified as `*' to indicate 0.0.0.0; the default is 127.0.0.1\. IPv6 numeric addresses must be specified inside of square brackets, e.g., [::1]:4081 to specify the IPv6 loopback address and TCP port 4081.

Note that this option is mutually-exclusive with the -httpd option and disables reading commands from standard input.

**-selfsignedok**

When verifying a host SSL certificate, allow it to be self-signed.

**-set** _toggle_

Sets the initial value of _toggle_ to **true**. The list of toggle names is under [TOGGLES](#Toggles) below.

**-socket**

Causes the emulator to create a Unix-domain socket when it starts, for use by script processes to send commands to the emulator. The socket is named **/tmp/x3sck.**_pid_. The **-p** option of _x3270if_ causes it to use this socket, instead of pipes specified by environment variables.

**-tn** _name_

Specifies the terminal name to be transmitted over the telnet connection. The default name is **IBM-**_model_name_**-E**, for example, **IBM-3278-4-E**.

Some hosts are confused by the **-E** suffix on the terminal name, and will ignore the extra screen area on models 3, 4 and 5\. Prepending an **s:** on the hostname, or setting the "s3270.extended" resource to "false", removes the **-E** from the terminal name when connecting to such hosts.

The name can also be specified with the "s3270.termName" resource.

**-trace**

Turns on data stream and event tracing at startup. The default trace file name is **/tmp/x3trc**.

**-tracefile** _file_

Specifies a file to save data stream and event traces into. If the name starts with `>>', data will be appended to the file.

**-tracefilesize** _size_

Places a limit on the size of a trace file. If this option is not specified, or is specified as **0** or **none**, the trace file size will be unlimited. The minimum size is 64 Kbytes. The value of _size_ can have a **K** or **M** suffix, indicating kilobytes or megabytes respectively. When the trace file reaches the size limit, it will be renamed with a `-' appended and a new file started.

**-user** _name_

Specifies the user name for RFC 4777 support.

**-utf8**

Forces the local codeset to be UTF-8, ignoring the locale or Windows codepage.

**-v**

Display the version and build options for **s3270** and exit.

**-verifycert**

For SSL or SSL/TLS connections, verify the host certificate, and do not allow the connection to complete unless it can be validated.

**-xrm** "s3270._resource_: _value_"

Sets the value of the named _resource_ to _value_. Resources control less common **s3270** options, and are defined under [RESOURCES](#Resources) below.

## Character Sets

The **-charset** option or the "s3270.charset" resource controls the EBCDIC host character set used by **s3270**. Available sets include:

Charset Name

Host Code Page

Character Set

belgian

500

iso8859-1

belgian-euro

1148

iso8859-15

bracket

037

iso8859-1

brazilian

275

iso8859-1

chinese-gb18030

1388

iso8859-1 + iso10646-1

cp1047

1047

iso8859-1

cp870

870

iso8859-2

finnish

278

iso8859-1

finnish-euro

1143

iso8859-15

french

297

iso8859-1

french-euro

1147

iso8859-15

german

273

iso8859-1

german-euro

1141

iso8859-15

greek

423

iso8859-7

hebrew

424

iso8859-8

icelandic

871

iso8859-1

icelandic-euro

1149

iso8859-15

italian

280

iso8859-1

italian-euro

1144

iso8859-15

japanese-kana

930

jisx0201.1976-0 + jisx0208.1983-0

japanese-latin

939

jisx0201.1976-0 + jisx0208.1983-0

norwegian

277

iso8859-1

norwegian-euro

1142

iso8859-15

russian

880

koi8-r

simplified-chinese

935

iso8859-1 + gb2312.1980-0

slovenian

870

iso8859-2

spanish

284

iso8859-1

spanish-euro

1145

iso8859-15

thai

1160

iso8859-11 tis620.2529-0

traditional-chinese

937

iso8859-1 + Big5-0

turkish

1026

iso8859-9

uk

285

iso8859-1

uk-euro

1146

iso8859-15

us-euro

1140

iso8859-15

us-intl

037

iso8859-1

The default character set is **bracket**, which is useful for common U.S. IBM hosts which use EBCDIC codes AD and BD for the `[' and `]' characters, respectively.

Note that any of the host code pages listed above can be specified by adding **cp** to the host code page, e.g., **cp037** for host code page 037\. Also note that the code pages available for a given version of **s3270** are displayed by the **-v** command-line option.

## NVT Mode

Some hosts use an ASCII front-end to do initial login negotiation, then later switch to 3270 mode. **s3270** will emulate an ANSI X3.64 terminal until the host places it in 3270 mode (telnet BINARY and SEND EOR modes, or TN3270E mode negotiation).

If the host later negotiates to stop functioning in 3270 mode, **s3270** will return to NVT emulation.

In NVT mode, **s3270** supports both character-at-a-time mode and line mode operation. You may select the mode with a menu option. When in line mode, the special characters and operational characteristics are defined by resources:

Mode/Character

Resource

Default

Translate CR to NL

s3270.icrnl

true

Translate NL to CR

s3270.inlcr

false

Erase previous character

s3270.erase

^?

Erase entire line

s3270.kill

^U

Erase previous word

s3270.werase

^W

Redisplay line

s3270.rprnt

^R

Ignore special meaning of next character

s3270.lnext

^V

Interrupt

s3270.intr

^C

Quit

s3270.quit

^\

End of file

s3270.eof

^D

## Toggles

**s3270** has a number of configurable modes which may be selected by the **-set** and **-clear** options. These names can also be used as the first parameter to the **Toggle** action.

**blankFill**

If set, **s3270** modifies interactive 3270 behavior in two ways. First, when a character is typed into a field, all nulls in the field to the left of that character are changed to blanks. This eliminates a common 3270 data-entry surprise. Second, in insert mode, trailing blanks in a field are treated like nulls, eliminating the annoying `lock-up' that often occurs when inserting into an field with (apparent) space at the end.

**lineWrap**

If set, the NVT terminal emulator automatically assumes a NEWLINE character when it reaches the end of a line.

**trace**

Turns on data stream and event tracing at start-up. Network traffic (both a hexadecimal representation and its interpretation) is logged to the file . The directory for the trace file can be changed with the "s3270.traceDir" resource. Script commands are also traced.

**screenTrace**

Turns on screen tracing at start-up. Each time the screen changes, its contents are appended to the file .

**aidWait**

Changes the behavior of actions that send an AID to the host (**Enter**, **Clear**, **PA** and **PF**). When set, these actions no longer block until the host unlocks the keyboard. It is up to the script to poll the prompt for the unlocked state, or to use the **Wait(Unlock)** action to wait for the unlock.

## Actions

Here is a complete list of basic s3270 actions. Script-specific actions are described on the [_x3270-script_(1)](x3270-script.html) manual page. )

Actions marked with an asterisk (*) may block, sending data to the host and possibly waiting for a response.

*Attn

attention key

BackSpace

move cursor left (or send ASCII BS)

BackTab

tab to start of previous input field

CircumNot

input "^" in NVT mode, or "¬" in 3270 mode

*Clear

clear screen

*Connect(_host_)

connect to _host_

*CursorSelect

Cursor Select AID

Delete

delete character under cursor (or send ASCII DEL)

DeleteField

delete the entire field

DeleteWord

delete the current or previous word

*Disconnect

disconnect from host

Down

move cursor down

Dup

duplicate field

*Enter

Enter AID (or send ASCII CR)

Erase

erase previous character (or send ASCII BS)

EraseEOF

erase to end of current field

EraseInput

erase all input fields

Execute(_cmd_)

execute a command in a shell

FieldEnd

move cursor to end of field

FieldMark

mark field

HexString(_hex_digits_)

insert control-character string

Home

move cursor to first input field

Insert

set insert mode

*Interrupt

send TELNET IP to host

Key(_keysym_)

insert key _keysym_

Key(0x_xx_)

insert key with character code _xx_

Left

move cursor left

Left2

move cursor left 2 positions

MonoCase

toggle uppercase-only mode

MoveCursor(_row_, _col_)

move cursor to (_row_,_col_)

Newline

move cursor to first field on next line (or send ASCII LF)

NextWord

move cursor to next word

*PA(_n_)

Program Attention AID (_n_ from 1 to 3)

*PF(_n_)

Program Function AID (_n_ from 1 to 24)

PreviousWord

move cursor to previous word

PrintText(_command_)

print screen text on printer

Quit

exit **s3270**

Redraw

redraw window

Reset

reset locked keyboard

Right

move cursor right

Right2

move cursor right 2 positions

*Script(_command_[,_arg_...])

run a script

*String(_string_)

insert string (simple macro facility)

*SysReq

System Request AID

Tab

move cursor to next input field

Toggle(_option_[,_set|clear_])

toggle an option

ToggleInsert

toggle insert mode

ToggleReverse

toggle reverse-input mode

*Transfer(_option_\=_value_...')

file transfer

Up

move cursor up

Note that certain parameters to s3270 actions (such as the names of files and keymaps) are subject to _substitutions_:

The character **~** at the beginning of a string is replaced with the user's home directory. A **~** character followed by a username is replaced with that user's home directory.

Environment variables are substituted using the Unix shell convention of $_name_ or ${_name_}.

Two special pseudo-environment variables are supported. ${TIMESTAMP} is replaced with a microsecond-resolution timestamp; ${UNIQUE} is replaced with a string guaranteed to make a unique filename (the process ID optionally followed by a dash and a string of digits). ${UNIQUE} is used to form trace file names.

## File Transfer

The **Transfer** action implements **IND$FILE** file transfer. This action requires that the **IND$FILE** program be installed on the IBM host, and that the 3270 cursor be located in a field that will accept a TSO or VM/CMS command.

Because of the complexity and number of options for file transfer, the parameters to the **Transfer** action take the unique form of _option_\=_value_, and can appear in any order. Note that if the _value_ contains spaces (such as a VM/CMS file name), then the entire parameter must be quoted, e.g., "HostFile=xxx foo a". The options are:

Option

Required?

Default

Other Values

Direction

No

receive

send

HostFile

Yes

LocalFile

Yes

Host

No

tso

vm, cics

Mode

No

ascii

binary

Cr

No

remove

add, keep

Remap

No

yes

no

Exist

No

keep

replace, append

Recfm

No

fixed, variable, undefined

Lrecl

No

Blksize

No

Allocation

No

tracks, cylinders, avblock

PrimarySpace

Sometimes

SecondarySpace

No

Avblock

Sometimes

BufferSize

No

4096

The option details are as follows.

**Direction**

**send** to send a file to the host, **receive** to receive a file from the host.

**HostFile**

The name of the file on the host.

**LocalFile**

The name of the file on the local workstation.

**Host**

The type of host (which dictates the form of the **IND$FILE** command): **tso** (the default), **vm** or **cics**.

**Mode**

Use **ascii** (the default) for a text file, which will be translated between EBCDIC and ASCII as necessary. Use **binary** for non-text files.

**Cr**

Controls how **Newline** characters are handled when transferring **Mode=ascii** files. **remove** (the default) strips **Newline** characters in local files before transferring them to the host. **add** adds **Newline** characters to each host file record before transferring it to the local workstation. **keep** preserves **Newline** characters when transferring a local file to the host.

**Remap**

Controls text translation for **Mode=ascii** files. The value **yes** (the default) causes s3270 to remap the text to ensure maximum compatibility between the workstation's character set and encoding and the host's EBCDIC code page. The value **no** causes s3270 to pass the text to or from the host as-is, leaving all translation to the **IND$FILE** program on the host.

**Exist**

Controls what happens when the destination file already exists. **keep** (the default) preserves the file, causing the **Transfer** action to fail. **replace** overwrites the destination file with the source file. **append** appends the source file to the destination file.

**Recfm**

Controls the record format of files created on the host. (TSO and VM hosts only.) **fixed** creates a file with fixed-length records. **variable** creates a file with variable-length records. **undefined** creates a file with undefined-length records (TSO hosts only). The **Lrecl** option controls the record length or maximum record length for **Recfm=fixed** and **Recfm=variable** files, respectively.

**Lrecl**

Specifies the record length (or maximum record length) for files created on the host. (TSO and VM hosts only.)

**Blksize**

Specifies the block size for files created on the host. (TSO and VM hosts only.)

**Allocation**

Specifies the units for the **PrimarySpace** and **SecondarySpace** options: **tracks**, **cylinders** or **avblock**. (TSO hosts only.)

**PrimarySpace**

Primary allocation for a file. The units are given by the **Allocation** option. Required when the **Allocation** is specified as something other than **default**. (TSO hosts only.)

**SecondarySpace**

Secondary allocation for a file. The units are given by the **Allocation** option. (TSO hosts only.)

**Avblock**

Average block size, required when **Allocation** specifies **avblock**. (TSO hosts only.)

**BufferSize**

Buffer size for DFT-mode transfers. Can range from 256 to 32768\. Larger values give better performance, but some hosts may not be able to support them.

There are also resources that control the default values for each of the file transfer parameters. These resources have the same names as the **Transfer** keywords, but with **ft** prepended. E.g., the default for the **Mode** keyword is the **s3270.ftMode** resource.

## The PrintText Action

The **PrintText** produces screen snapshots in a number of different forms. The default form wth no arguments sends a copy of the screen to the default printer. A single argument is the command to use to print, e.g., **lpr**.

Multiple arguments can include keywords to control the output of **PrintText**:

**file** _filename_

Save the output in a file.

**html**

Save the output as HTML. This option implies **file**.

**rtf**

Save the output as RichText. This option implies **file**. The font defaults to **Courier New** and the point size defaults to 8\. These can be overridden by the **printTextFont** and **printTextSize** resources, respectively.

**string**

Return the output as a string. This can only be used from scripts.

**modi**

Render modified fields in italics.

**caption** _text_

Add the specified _text_ as a caption above the output. Within _text_, the special sequence **%T%** will be replaced with a timestamp.

**command** _command_

Directs the output to a command. This allows one or more of the other keywords to be specified, while still sending the output to the printer.

## Nested Scripts

There are several types of nested script functions available.

**The String Action**

The simplest method for nested scripts is provided via the **String** action. The arguments to **String** are one or more double-quoted strings which are inserted directly as if typed. The C backslash conventions are honored as follows. (Entries marked * mean that after sending the AID code to the host, **s3270** will wait for the host to unlock the keyboard before further processing the string.)

\b

Left

\e_xxxx_

EBCDIC character in hex

\f

Clear*

\n

Enter*

\pa_n_

PA(_n_)*

\pf_nn_

PF(_nn_)*

\r

Newline

\t

Tab

\T

BackTab

\u_xxxx_

Unicode character in hex

\x_xxxx_

Unicode character in hex

Note that the numeric values for the \e, \u and \x sequences can be abbreviated to 2 digits. Note also that EBCDIC codes greater than 255 and some Unicode character codes represent DBCS characters, which will work only if s3270 is built with DBCS support and the host allows DBCS input in the current field.

**Note:** The strings are in ASCII and converted to EBCDIC, so beware of inserting control codes.

There is also an alternate form of the **String** action, **HexString**, which is used to enter non-printing data. The argument to **HexString** is a string of hexadecimal digits, two per character. A leading 0x or 0X is optional. In 3270 mode, the hexadecimal data represent EBCDIC characters, which are entered into the current field. In NVT mode, the hexadecimal data represent ASCII characters, which are sent directly to the host.

**The Script Action**

This action causes **s3270** to start a child process which can execute **s3270** actions. Standard input and output from the child process are piped back to **s3270**. The **Script** action is fully documented in [_x3270-script_(1)](x3270-script.html).

## Passthru

**s3270** supports the Sun _telnet-passthru_ service provided by the _in.telnet-gw_ server. This allows outbound telnet connections through a firewall machine. When a **p:** is prepended to a hostname, **s3270** acts much like the _itelnet_(1) command. It contacts the machine named **internet-gateway** at the port defined in **/etc/services** as **telnet-passthru** (which defaults to 3514). It then passes the requested hostname and port to the **in.telnet-gw** server.

## Proxy

The **-proxy** option or the **s3270.proxy** resource causes s3270 to use a proxy server to connect to the host. The syntax of the option or resource is:

> _type_:_host_[:_port_]

The supported values for _type_ are:

Proxy Type

Protocol

Default Port

http

RFC 2817 HTTP tunnel (squid)

3128

passthru

Sun in.telnet-gw

none

socks4

SOCKS version 4

1080

socks5

SOCKS version 5 (RFC 1928)

1080

telnet

No protocol (just send **connect** _host port_)

none

The special types **socks4a** and **socks5d** can also be used to force the proxy server to do the hostname resolution for the SOCKS protocol.

## Resources

Certain **s3270** options can be configured via resources. Resources are defined by **-xrm** options. The definitions are similar to X11 resources, and use a similar syntax. The resources available in **s3270** are:

Resource

Default

Option

Purpose

blankFill

False

-set blankFill

Blank Fill mode

charset

bracket

-charset

EBCDIC character set

dbcsCgcsgid

Override DBCS CGCSGID

dsTrace

False

-trace

Data stream tracing

eof

^D

NVT-mode EOF character

erase

^H

NVT-mode erase character

extended

True

Use 3270 extended data stream

eventTrace

False

-trace

Event tracing

icrnl

False

Map CR to NL on NVT-mode input

inlcr

False

Map NL to CR in NVT-mode input

intr

^C

NVT-mode interrupt character

kill

^U

NVT-mode kill character

lineWrap

False

-set lineWrap

NVT line wrap mode

lnext

^V

NVT-mode lnext character

m3279

[(note 1)](#rn1)

-model

3279 (color) emulation

monoCase

False

-set monoCase

Mono-case mode

numericLock

False

Lock keyboard for numeric field error

oerrLock

False

Lock keyboard for input error

oversize

-oversize

Oversize screen dimensions

port

telnet

-port

Non-default TCP port

quit

^\

NVT-mode quit character

rprnt

^R

NVT-mode reprint character

sbcsCgcsgid

Override SBCS CGCSGID

secure

False

Disable "dangerous" options

termName

[(note 2)](#rn2)

-tn

TELNET terminal type string

traceDir

/tmp

Directory for trace files

traceFile

[(note 3)](#rn3)

-tracefile

File for trace output

werase

^W

NVT-mode word-erase character

> _Note 1_: **m3279** defaults to **False**. It can be forced to **True** with the proper **-model** option.

> _Note 2_: The default terminal type string is constructed from the model number, color emulation, and extended data stream modes. E.g., a model 2 with color emulation and the extended data stream option would be sent as **IBM-3279-2-E**. Note also that when TN3270E mode is used, the terminal type is always sent as 3278, but this does not affect color capabilities.

> _Note 3_: The default trace file is **x3trc.**_pid_ in the directory specified by the **traceDir** resource.

If more than one **-xrm** option is given for the same resource, the last one on the command line is used.

## Files

/usr/local/lib/x3270/ibm_hosts

## See Also

[x3270-script(1),](x3270-script.html) [x3270(1)](x3270-man.html), [c3270(1)](c3270-man.html), [tcl3270(1)](tcl3270-man.html), telnet(1), tn3270(1)<br>
Data Stream Programmer's Reference, IBM GA23-0059<br>
Character Set Reference, IBM GA27-3831<br>
RFC 1576, TN3270 Current Practices<br>
RFC 1646, TN3270 Extensions for LUname and Printer Selection<br>
RFC 2355, TN3270 Enhancements

## Copyrights

Copyright © 1993-2015, Paul Mattes.<br>
Copyright © 2004-2005, Don Russell.<br>
Copyright © 2004, Dick Altenbern.<br>
Copyright © 1990, Jeff Sparkes.<br>
Copyright © 1989, Georgia Tech Research Corporation (GTRC), Atlanta, GA 30332.<br>
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

*

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

*

Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

*

Neither the names of Paul Mattes, Don Russell, Dick Altenbern, Jeff Sparkes, GTRC nor the names of their contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PAUL MATTES, DON RUSSELL, DICK ALTENBERN, JEFF SPARKES AND GTRC "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL PAUL MATTES, DON RUSSELL, DICK ALTENBERN, JEFF SPARKES OR GTRC BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## Version

s3270 3.4ga4

--------------------------------------------------------------------------------

_This HTML document and the accompanying troff document were generated with a set of write-only **m4** macros and the powerful **vi** editor.<br>
Last modified 19 June 2015._
