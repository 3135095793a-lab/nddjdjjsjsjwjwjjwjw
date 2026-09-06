"""Inspect actual DEX class_def entries, not incidental string references."""
import struct
import zipfile

REQUIRED = {
    'Lorg/autojs/autojs/runtime/ScriptRuntime;',
    'Lorg/autojs/autojs/engine/LoopBasedJavaScriptEngine;',
}

def defined_classes(data):
    if len(data) < 112 or not data.startswith(b'dex\n'):
        raise ValueError('Unsupported or truncated DEX')
    def word(offset):
        return struct.unpack_from('<I', data, offset)[0]
    strings_size, strings_off = word(56), word(60)
    types_size, types_off = word(64), word(68)
    classes_size, classes_off = word(96), word(100)
    for count, offset, width in ((strings_size, strings_off, 4), (types_size, types_off, 4), (classes_size, classes_off, 32)):
        if offset + count * width > len(data):
            raise ValueError('DEX table out of bounds')
    result = set()
    for i in range(classes_size):
        class_index = word(classes_off + i * 32)
        if class_index >= types_size:
            raise ValueError('Invalid DEX class index')
        string_index = word(types_off + class_index * 4)
        if string_index >= strings_size:
            raise ValueError('Invalid DEX string index')
        pos = word(strings_off + string_index * 4)
        for _ in range(5):
            if pos >= len(data):
                raise ValueError('Truncated DEX string length')
            byte = data[pos]
            pos += 1
            if byte < 128:
                break
        else:
            raise ValueError('Invalid DEX string length')
        end = data.index(b'\0', pos)
        result.add(data[pos:end].decode('utf-8', errors='replace'))
    return result

def verify_engine(apk):
    classes = set()
    with zipfile.ZipFile(apk) as archive:
        for name in archive.namelist():
            if '/' not in name and name.startswith('classes') and name.endswith('.dex'):
                classes.update(defined_classes(archive.read(name)))
    missing = REQUIRED - classes
    if missing:
        raise ValueError('APK missing engine class definitions: ' + ', '.join(sorted(missing)))
    return {'requiredClassDefinitions': sorted(REQUIRED), 'totalClassDefinitions': len(classes), 'runtimeVerified': False}
