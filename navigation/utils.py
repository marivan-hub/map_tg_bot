def parse_building_from_code(code):
    suffixes = ['МТ','БМ','КК','B2','B4','B5','B6','B7','B8','B9','C1','C3','Т','К','Э','М','Л','Ю','Х']
    prefixes = ['КХ','К']

    for sfx in sorted(suffixes, key=lambda x: -len(x)):
        if code.endswith(sfx):
            return sfx
    for pfx in sorted(prefixes, key=lambda x: -len(x)):
        if code.startswith(pfx):
            return pfx
    return "DEFAULT"
