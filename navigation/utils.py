def normalize(s: str) -> str:
    """Normalizes string by mapping Cyrillic homoglyphs to Latin equivalents."""
    trans_map = str.maketrans({
        '\u0410': 'A',  # А
        '\u0411': 'B',  # Б
        '\u0412': 'B',  # В
        '\u0415': 'E',  # Е
        '\u041A': 'K',  # К
        '\u041C': 'M',  # М
        '\u041D': 'H',  # Н
        '\u041E': 'O',  # О
        '\u041F': 'P',  # П
        '\u0420': 'P',  # Р
        '\u0421': 'C',  # С
        '\u0422': 'T',  # Т
        '\u0423': 'Y',  # У
        '\u0425': 'X',  # Х
        '\u041B': 'L',  # Л
        '\u042D': 'E',  # Э
        '\u042E': 'YU', # Ю
    })
    return s.upper().translate(trans_map)

def parse_building_from_code(code):
    code = normalize(code)
    # Updated suffixes and prefixes to normalized (Latin) forms
    suffixes = ['MT', 'BM', 'KK', 'B2', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'C1', 'C3', 'T', 'K', 'E', 'M', 'L', 'YU', 'X']
    prefixes = ['KX', 'K']

    for sfx in sorted(suffixes, key=lambda x: -len(x)):
        if code.endswith(sfx):
            return sfx
    for pfx in sorted(prefixes, key=lambda x: -len(x)):
        if code.startswith(pfx):
            if pfx == 'K' or pfx == 'KX':
                return 'B4'
            return pfx
    return "DEFAULT"