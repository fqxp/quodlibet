# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys, sre, string, locale

def gettext_install(domain, localedir=None, unicode=False):
    import gettext, __builtin__
    t = gettext.translation(domain, localedir, fallback=True)
    if unicode: gettext, ngettext = t.ugettext, t.ungettext
    else: gettext, ngettext = t.gettext, t.ngettext
    __builtin__.__dict__["_"] = gettext
    __builtin__.__dict__["ngettext"] = ngettext

def gtk_init():
    import gtk, gobject
    if gtk.pygtk_version > (2, 8):
        gobject.type_register = lambda Kind: True

    # http://bugzilla.gnome.org/show_bug.cgi?id=318953
    if gtk.gtk_version < (2, 8, 8):
        class TVProxy(gtk.TreeView):
            def set_search_equal_func(self, func, *args): pass
        gtk.TreeView = TVProxy

def ctypes_init():
    try: import ctypes
    except ImportError: pass
    else:
        ctypes.c_int8 = ctypes.c_byte
        ctypes.c_uint8 = ctypes.c_ubyte
        from ctypes import c_short, c_int, c_long, c_longlong
        for kind in [c_short, c_int, c_long, c_longlong]:
            if ctypes.sizeof(kind) == 2: ctypes.c_int16 = kind
            elif ctypes.sizeof(kind) == 4: ctypes.c_int32 = kind
            elif ctypes.sizeof(kind) == 8: ctypes.c_int64 = kind
        from ctypes import c_ushort, c_uint, c_ulong, c_ulonglong
        for kind in [c_ushort, c_uint, c_ulong, c_ulonglong]:
            if ctypes.sizeof(kind) == 2: ctypes.c_uint16 = kind
            elif ctypes.sizeof(kind) == 4: ctypes.c_uint32 = kind
            elif ctypes.sizeof(kind) == 8: ctypes.c_uint64 = kind

class InstanceTracker(object):
    """A mixin for GObjects to return a list of all alive objects
    of a given type. Note that it must be used with a GObject or
    something with a connect method and destroy signal."""
    __kinds = {}

    def _register_instance(self, klass=None):
        """Register this object to be returned in the active instance list."""
        if klass is None: klass = type(self)
        self.__kinds.setdefault(klass, []).append(self)
        self.connect('destroy', self.__kinds[klass].remove)

    def instances(klass): return klass.__kinds.get(klass, [])
    instances = classmethod(instances)

class OptionParser(object):
    def __init__(self, name, version, description=None, usage=None):
        self.__name = name
        self.__version = version
        self.__args = {}
        self.__translate_short = {}
        self.__translate_long = {}
        self.__help = {}
        self.__usage = usage
        self.__description = description
        self.add(
            "help", shorts="h", help=_("Display brief usage information"))
        self.add(
            "version", shorts="v", help=_("Display version and copyright"))

    def add(self, canon, help=None, arg="", shorts="", longs=[]):
        self.__args[canon] = arg
        for s in shorts: self.__translate_short[s] = canon
        for l in longs: self.__translate_long[l] = canon
        if help: self.__help[canon] = help

    def __shorts(self):
        shorts = ""
        for short, canon in self.__translate_short.items():
            shorts += short + (self.__args[canon] and "=" or "")
        return shorts

    def __longs(self):
        longs = []
        for long, arg in self.__args.items():
            longs.append(long + (arg and "=" or ""))
        for long, canon in self.__translate_long.items():
            longs.append(long + (self.__args[canon] and "=" or ""))
        return longs

    def __format_help(self, opt, space):
        if opt in self.__help:
            help = self.__help[opt]
            if self.__args[opt]:
                opt = "%s=%s" % (opt, self.__args[opt])
            return "  --%s %s\n" % (opt.ljust(space), help)
                
        else: return ""

    def help(self):
        l = 0
        for k in self.__help.keys():
            l = max(l, len(k) + len(self.__args.get(k, "")) + 4)

        if self.__usage: s = _("Usage: %s %s") % (sys.argv[0], self.__usage)
        else: s = _("Usage: %s %s") % (sys.argv[0], _("[options]"))
        s += "\n"
        if self.__description:
            s += "%s - %s\n" % (self.__name, self.__description)
        s += "\n"
        keys = self.__help.keys()
        keys.sort()
        try: keys.remove("help")
        except ValueError: pass
        try: keys.remove("version")
        except ValueError: pass
        for h in keys: s += self.__format_help(h, l)
        if keys: s += "\n"
        s += self.__format_help("help", l)
        s += self.__format_help("version", l)
        return s

    def set_help(self, newhelp):
        self.__help = newhelp

    def version(self):
        return _("""\
%s %s - <quodlibet@lists.sacredchao.net>
Copyright 2004-2005 Joe Wreschnig, Michael Urman, and others

This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
""") % (self.__name, self.__version)

    def parse(self, args=None):
        if args is None: args = sys.argv[1:]
        from getopt import getopt, GetoptError
        try: opts, args = getopt(args, self.__shorts(), self.__longs())
        except GetoptError, s:
            s = str(s)
            text = []
            if "not recognized" in s:
                text.append(
                    _("E: Option '%s' not recognized.") % s.split()[1])
            elif "requires argument" in s:
                text.append(
                    _("E: Option '%s' requires an argument.") % s.split()[1])
            elif "unique prefix" in s:
                text.append(
                    _("E: '%s' is not a unique prefix.") % s.split()[1])
            if "help" in self.__args:
                text.append(_("E: Try %s --help.") % sys.argv[0])

            raise SystemExit(to("\n".join(text)))
        else:
            transopts = {}
            for o, a in opts:
                if o.startswith("--"):
                    o = self.__translate_long.get(o[2:], o[2:])
                elif o.startswith("-"):
                    o = self.__translate_short.get(o[1:], o[1:])
                if o == "help":
                    print self.help()
                    raise SystemExit
                elif o == "version":
                    print self.version()
                    raise SystemExit
                if self.__args[o]: transopts[o] = a
                else: transopts[o] = True

            return transopts, args

def to(string, frm="utf-8"):
    """Convert a string to the system encoding; used if you need to
    print to stdout. If you pass in a str (rather than a unicode) you
    should specify the encoding it's in with 'frm'."""
    enc = locale.getpreferredencoding()
    if isinstance(string, unicode): return string.encode(enc, "replace")
    else: return string.decode(frm).encode(enc, "replace")

def mtime(filename):
    """Return the mtime of a file, or 0 if an error occurs."""
    try: return os.path.getmtime(filename)
    except OSError: return 0

def size(filename):
    """Return the size of a file, or 0 if an error occurs."""
    try: return os.path.getsize(filename)
    except OSError: return 0

def mkdir(dir):
    """Make a directory, including all its parent directories. This does not
    raise an exception if the directory already exists (and is a
    directory)."""
    if not os.path.isdir(dir):
        os.makedirs(dir)

def escape(str):
    """Escape a string in a manner suitable for XML/Pango."""
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def unescape(str):
    """Unescape a string in a manner suitable for XML/Pango."""
    return str.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

def re_esc(str):
    return "".join(map(
        lambda a: (a in "/.^$*+?{,}\\[]|()<>#=!:" and "\\" + a) or a, str))
sre.escape = re_esc

def parse_time(timestr):
    """Parse a time string in hh:mm:ss, mm:ss, or ss format."""
    if timestr[0:1] == "-":
        m = -1
        timestr = timestr[1:]
    else: m = 1

    try:
        return m * reduce(lambda s, a: s * 60 + int(a),
                          sre.split(":|\\.", timestr), 0)
    except (ValueError, sre.error):
        return 0

RATING_PRECISION = 0.25
def format_rating(value):
    """Turn a number into a sequence of music notes."""
    return (u'\u266a' * int(round((1/RATING_PRECISION) * value)))

def format_size(size):
    """Turn an integer size value into something human-readable."""
    if size >= 1024*1024 * 10:
        return "%.1fMB" % (float(size) / (1024*1024))
    elif size >= 1024*1024:
        return "%.2fMB" % (float(size) / (1024*1024))
    elif size >= 1024 * 10:
        return "%dKB" % int(size / 1024)
    elif size >= 1024:
        return "%.2fKB" % (float(size) / 1024)
    else:
        return "%dB" % size

def format_time(time):
    """Turn a time value in seconds into hh:mm:ss or mm:ss."""
    if time < 0:
        time = abs(time)
        prefix = "-"
    else: prefix = ""
    if time >= 3600: # 1 hour
        # time, in hours:minutes:seconds
        return "%s%d:%02d:%02d" % (prefix, time // 3600,
                                   (time % 3600) // 60, time % 60)
    else:
        # time, in minutes:seconds
        return "%s%d:%02d" % (prefix, time // 60, time % 60)

def format_time_long(time):
    """Turn a time value in seconds into x hours, x minutes, etc."""
    if time < 1: return _("No time information")
    cutoffs = [
        (60, "%d seconds", "%d second"),
        (60, "%d minutes", "%d minute"),
        (24, "%d hours", "%d hour"),
        (365, "%d days", "%d day"),
        (None, "%d years", "%d year"),
    ]
    time_str = []
    for divisor, plural, single in cutoffs:
        if time < 1: break
        if divisor is None: time, unit = 0, time
        else: time, unit = divmod(time, divisor)
        if unit: time_str.append(ngettext(single, plural, unit) % unit)
    time_str.reverse()
    if len(time_str) > 2: time_str.pop()
    return ", ".join(time_str)

# http://developer.gnome.org/doc/API/2.0/glib/glib-running.html
if "G_FILENAME_ENCODING" in os.environ:
    fscoding = os.environ["G_FILENAME_ENCODING"].split(",")[0]
    if fscoding == "@locale": fscoding = locale.getpreferredencoding()
elif "G_BROKEN_FILENAMES" in os.environ:
    fscoding = locale.getpreferredencoding()
else: fscoding = "utf-8"

def fsdecode(s):
    """Decoding a string according to the filesystem encoding."""
    if isinstance(s, unicode): return s
    else: return decode(s, fscoding)

def fsencode(s):
    """Encode a string according to the filesystem encoding, replacing
    errors."""
    if isinstance(s, str): return s
    else: return s.encode(fscoding, 'replace')

def decode(s, charset="utf-8"):
    """Decode a string; if an error occurs, replace characters and append
    a note to the string."""
    try: return s.decode(charset)
    except UnicodeError:
        return s.decode(charset, "replace") + " " + _("[Invalid Encoding]")

def encode(s, charset="utf-8"):
    """Encode a string; if an error occurs, replace characters and append
    a note to the string."""
    try: return s.encode(charset)
    # FIXME: Can *this* happen?
    except UnicodeError:
        return (s + " " + _("[Invalid Encoding]")).encode(charset, "replace")

def title(string):
    """Title-case a string using a less destructive method than str.title."""
    if not string: return ""
    new_string = string[0].capitalize()
    cap = False
    for s in string[1:]:
        if s.isspace(): cap = True
        elif cap and s.isalpha():
            cap = False
            s = s.capitalize()
        else: cap = False
        new_string += s
    return new_string

def iscommand(s):
    """True if 's' exists in the user's path, or is a fully-qualified
    existing path."""

    if s == "" or os.path.sep in s:
        return (os.path.isfile(s) and os.access(s, os.X_OK))
    else:
        s = s.split()[0]
        for p in os.defpath.split(os.path.pathsep):
            p2 = os.path.join(p, s)
            if (os.path.isfile(p2) and os.access(p2, os.X_OK)):
                return True
        else: return False

def capitalize(str):
    """Capitalize a string, not affecting any character after the first."""
    return str[:1].upper() + str[1:]

def split_value(s, splitters=["/", "&", ","]):
    if not splitters: return [s.strip()]
    values = s.split("\n")
    for spl in splitters:
        spl = sre.compile(r"\b\s*%s\s*\b" % sre.escape(spl), sre.UNICODE)
        new_values = []
        for v in values:
            new_values.extend(map(string.strip, spl.split(v)))
        values = new_values
    return values

def split_title(s, splitters=["/", "&", ","]):
    title, subtitle = find_subtitle(s)
    if not subtitle: return (s, [])
    else: return (title.strip(), split_value(subtitle, splitters))

def split_people(s, splitters=["/", "&", ","]):
    title, subtitle = find_subtitle(s)
    if not subtitle:
        parts = s.split(" ")
        if len(parts) > 2:
            for feat in ["feat.", "featuring", "feat", "with", "w/"]:
                try:
                    i = map(string.lower, parts).index(feat)
                    orig = " ".join(parts[:i])
                    others = " ".join(parts[i+1:])
                    return (orig, split_value(others, splitters))
                except (ValueError, IndexError): pass
        return (s, [])
    else:
        for feat in ["feat.", "featuring", "feat", "with", "w/"]:
            if subtitle.startswith(feat):
                subtitle = subtitle.replace(feat, "", 1).lstrip()
                break
        values = split_value(subtitle, splitters)
        return (title.strip(), values)

def split_album(s):
    name, disc = find_subtitle(s)
    if not disc:
        parts = s.split(" ")
        if len(parts) > 2:
            lower = parts[-2].lower()
            if "disc" in lower or "disk" in lower:
                return (" ".join(parts[:-2]), parts[-1])
        return (s, None)
    else:
        parts = disc.split()
        if (len(parts) == 2 and
            parts[0].lower() in ["disc", "disk", "cd", "vol", "vol."]):
            try: return (name, parts[1])
            except: return (s, None)
        else: return (s, None)

def find_subtitle(title):
    if isinstance(title, str): title = title.decode('utf-8', 'replace')
    for pair in [u"[]", u"()", u"~~", u"--", u"\u301c\u301c"]:
        if pair[0] in title[:-1] and title.endswith(pair[1]):
            r = len(pair[1])
            l = title[0:-r].rindex(pair[0])
            if l != 0:
                subtitle = title[l+len(pair[0]):-r]
                title = title[:l]
                return title.rstrip(), subtitle
    else: return title, None

def unexpand(filename):
    """Replace the user's home directory with ~/, if it appears at the
    start of the path name."""
    if filename == os.path.expanduser("~"): return "~"
    elif filename.startswith(os.path.expanduser("~/")):
        filename = filename.replace(os.path.expanduser("~/"), "~/", 1)
    return filename

def website(site):
    site = site.replace("\\", "\\\\").replace("\"", "\\\"")
    for s in (["sensible-browser", "gnome-open"] +
              os.environ.get("BROWSER","").split(":")):
        if iscommand(s):
            if "%s" in s:
                s = s.replace("%s", '"' + site + '"')
                s = s.replace("%%", "%")
            else: s += " \"%s\"" % site
            if os.system(s + " &") == 0: return True
    else: return False

def tag(name, cap=True):
    # Return a 'natural' version of the tag for human-readable bits.
    # Strips ~ and ~# from the start and runs it through a map (which
    # the user can configure).
    if not name: return _("Invalid tag")
    else:
        def readable(tag):
            try:
                if tag[0] == "~":
                    if tag[1] == "#": tag = tag[2:]
                    else: tag = tag[1:]
            except IndexError: return _("Invalid tag")
            else: return _(HEADERS_FILTER.get(tag, tag.replace("_", " ")))
        parts = map(readable, tagsplit(name))
        if cap: parts = map(capitalize, parts)
        return " / ".join(parts)

def tagsplit(tag):
    """Split a (potentially) tied tag into a list of atomic tags. Two ~~s
    make the next tag prefixed with a ~, so ~foo~~bar => [foo, ~bar]."""
    if "~" in tag[1:]:
        if tag.startswith("~") and not tag.startswith("~#"): tag = tag[1:]
        tags = []
        front = ""
        for part in tag.split("~"):
            if part:
                tags.append(front + part)
                front = ""
            else: front = "~"
        return tags
    else: return [tag]

HEADERS_FILTER = { "tracknumber": "track",
                   "discnumber": "disc",
                   "labelid": "label ID",
                   "bpm": "BPM",
                   "isrc": "ISRC",
                   "lastplayed": "last played",
                   "filename": "full name",
                   "playcount": "plays",
                   "skipcount": "skips",
                   "mtime": "modified",
                   "mountpoint": "mount point",
                   "basename": "filename",
                   "dirname": "directory" }

