"""Named themes and optional #RRGGBB overrides in preferences.json."""
BASE = {'BG': '#b09277', 'PANEL': '#b09277', 'EDGE': '#715240', 'TEXT': '#0c0a08',
        'DIM': '#493728', 'ACCENT': '#69b96a', 'YELLOW': '#f5f450', 'CYAN': '#14100c',
        'PURPLE': '#c390dc', 'CURSOR': '#eaeac6', 'SELECT': '#56403a', 'WELL': '#000000',
        'CREAM': '#e9e8c8', 'SLIDER': '#a92e42', 'SCOPE': '#cb4557',
        'AUTOMATION': '#65dbc5', 'AUTOMATION_DIM': '#52766e', 'REC_ARM': '#b53242',
        'REC_SLIDER': '#348bdb'}
VARIANTS = {'Classic crimson': {}, 'Charcoal crimson': {
    'BG':'#303236','PANEL':'#303236','TEXT':'#f2efdc','DIM':'#c2bcb0','CYAN':'#f2efdc',
    'EDGE':'#111318','CREAM':'#e9e8d8','SELECT':'#63313e','WELL':'#101113'},
    'High contrast': {'BG':'#d2c6ac','PANEL':'#d2c6ac','TEXT':'#000000','DIM':'#30251e',
    'EDGE':'#38281f','CREAM':'#ffffff','SELECT':'#42242a','SLIDER':'#be2539','SCOPE':'#e64b5c'}}


def palette(appearance):
    colors={**BASE,**VARIANTS.get(appearance.get('theme'),{})}
    for key,value in appearance.get('colors',{}).items():
        key=key.upper()
        if key in colors and isinstance(value,str) and len(value)==7 and value.startswith('#'):
            try:int(value[1:],16)
            except ValueError:continue
            colors[key]=value
    return {k:tuple(int(v[i:i+2],16) for i in (1,3,5)) for k,v in colors.items()}
