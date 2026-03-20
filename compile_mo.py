import struct

BACKSLASH = chr(92)

def unescape(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    result = []
    i = 0
    while i < len(s):
        if s[i] == BACKSLASH and i + 1 < len(s):
            c = s[i+1]
            if c == 'n':
                result.append('\n')
            elif c == 't':
                result.append('\t')
            elif c == '"':
                result.append('"')
            elif c == BACKSLASH:
                result.append(BACKSLASH)
            else:
                result.append(c)
            i += 2
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


def parse_po(po_path):
    messages = {}
    with open(po_path, encoding='utf-8') as f:
        lines = f.readlines()
    pending_id = []
    pending_str = []
    in_msgid = False
    in_msgstr = False

    def flush():
        mid = ''.join(pending_id)
        mstr = ''.join(pending_str)
        if mid:
            messages[mid] = mstr
        pending_id.clear()
        pending_str.clear()

    for line in lines:
        line = line.rstrip('\n')
        stripped = line.strip()
        if stripped.startswith('#') or stripped == '':
            if in_msgid or in_msgstr:
                flush()
                in_msgid = False
                in_msgstr = False
            continue
        if stripped.startswith('msgid '):
            if in_msgid or in_msgstr:
                flush()
            in_msgid = True
            in_msgstr = False
            pending_id.append(unescape(stripped[6:]))
        elif stripped.startswith('msgstr '):
            in_msgstr = True
            in_msgid = False
            pending_str.append(unescape(stripped[7:]))
        elif stripped.startswith('"') and in_msgid:
            pending_id.append(unescape(stripped))
        elif stripped.startswith('"') and in_msgstr:
            pending_str.append(unescape(stripped))

    if pending_id or pending_str:
        flush()

    messages.pop('', None)
    return messages


def write_mo(messages, mo_path):
    keys = sorted(messages.keys())
    n = len(keys)
    MAGIC = 0x950412de

    ids_buf = b''
    strs_buf = b''
    id_offsets = []
    str_offsets = []

    for k in keys:
        v = messages[k]
        kb = k.encode('utf-8')
        vb = v.encode('utf-8')
        id_offsets.append((len(kb), len(ids_buf)))
        str_offsets.append((len(vb), len(strs_buf)))
        ids_buf += kb + b'\x00'
        strs_buf += vb + b'\x00'

    # 28 bytes header + n*8 id table + n*8 str table, then ids_buf, then strs_buf
    ids_start = 28 + n * 16
    strs_start = ids_start + len(ids_buf)

    out = struct.pack('<IIIIIII', MAGIC, 0, n, 28, 28 + n * 8, 0, 0)
    for (klen, koff) in id_offsets:
        out += struct.pack('<II', klen, ids_start + koff)
    for (vlen, voff) in str_offsets:
        out += struct.pack('<II', vlen, strs_start + voff)
    out += ids_buf + strs_buf

    with open(mo_path, 'wb') as f:
        f.write(out)
    print(f"Compiled {n} messages to {mo_path}")


if __name__ == '__main__':
    parse_and_write = True
    messages = parse_po('locale/fr/LC_MESSAGES/django.po')
    write_mo(messages, 'locale/fr/LC_MESSAGES/django.mo')
