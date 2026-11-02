from pathlib import Path
import re

p = Path('resolver_monolithic_rc10.c')
s = p.read_text(encoding='utf-8')

# Canonical INI geometry from v1.0.23 FIX3/P3N lineage.
s = s.replace('#define ROW_H           32', '#define ROW_H           34')
s = s.replace('AoE2DE_P3O_54800_MONOLITHIC_RC10.log', 'AoE2DE_P3O_54800_MONOLITHIC_RC12.log')
s = s.replace('AOE2DE 101.103.54800.0 P3O MONOLITHIC RC10', 'AOE2DE 101.103.54800.0 P3O MONOLITHIC RC12')
s = s.replace('P3O54800MonolithicRC10', 'P3O54800MonolithicRC12')

# The schema probe proved the canonical catalog layout:
# [Catalog] categories=A pie|Caballería|... and one key per category.
new_load = r'''static void load_catalog(void){
    choose_ini();
    g_unitCount=g_catCount=0;
    wchar_t cats[4096]={0};
    DWORD cn=GetPrivateProfileStringW(L"Catalog",L"categories",L"",cats,4096,g_ini);
    if(cn){
        wchar_t*p0=cats;
        while(*p0&&g_catCount<MAX_CATS){
            wchar_t*cut=wcschr(p0,L'|');
            if(cut)*cut=0;
            wchar_t*name=trimw(p0);
            if(*name){
                int ci=add_cat(name);
                wchar_t entries[32768]={0};
                DWORD en=GetPrivateProfileStringW(L"Catalog",name,L"",entries,32768,g_ini);
                int got=en?parse_list(entries,ci):0;
                logf0("CAT_SCHEMA exact name=%ls entries=%d\\n",name,got);
            }
            if(!cut)break;
            p0=cut+1;
        }
    }
    if(!g_unitCount||!g_catCount){
        g_unitCount=g_catCount=0;
        wchar_t cycle[32768]={0};
        if(ini_str(L"unit_cycle",cycle,32768)){
            int ci=add_cat(L"Todos");
            parse_list(cycle,ci);
        }
    }
    if(!g_unitCount||!g_catCount){g_unitCount=g_catCount=0;fallback_catalog();}
    int initial=ini_int(L"unit_id",g_units[0].id);
    for(int i=0;i<g_unitCount;i++)if(g_units[i].id==initial){g_selected=i;break;}
    logf0("CATALOG units=%d categories=%d schema=Catalog/categories ini=%ls selected_id=%d\\n",g_unitCount,g_catCount,g_ini,g_units[(int)g_selected].id);
    for(int i=0;i<g_catCount;i++)logf0("CATEGORY index=%d name=%ls count=%d\\n",i,g_cats[i].name,g_cats[i].count);
}'''
pat = r'static void load_catalog\(void\)\{.*?\}\n\nstatic int world_probe'
s, n = re.subn(pat, new_load + '\n\nstatic int world_probe', s, flags=re.S)
if n != 1:
    raise SystemExit(f'load_catalog replacement count={n}')

# P3N RC5 search was global and accent-insensitive, not category-local.
new_search = r'''static wchar_t fold_es(wchar_t c){
    c=towlower(c);
    switch(c){
        case L'á':case L'à':case L'ä':case L'â':return L'a';
        case L'é':case L'è':case L'ë':case L'ê':return L'e';
        case L'í':case L'ì':case L'ï':case L'î':return L'i';
        case L'ó':case L'ò':case L'ö':case L'ô':return L'o';
        case L'ú':case L'ù':case L'ü':case L'û':return L'u';
        default:return c;
    }
}
static int contains_fold(const wchar_t*s,const wchar_t*q){
    if(!q||!*q)return 1;
    for(;*s;s++){
        const wchar_t*a=s,*b=q;
        while(*a&&*b&&fold_es(*a)==fold_es(*b)){a++;b++;}
        if(!*b)return 1;
    }
    return 0;
}
static int unit_matches(int ui){
    if(!g_searchText[0])return 1;
    wchar_t idbuf[24];wsprintfW(idbuf,L"%d",g_units[ui].id);
    return contains_fold(g_units[ui].name,g_searchText)||wcsstr(idbuf,g_searchText)!=NULL;
}
static void rebuild_view(void){
    g_viewCount=0;
    if(g_searchText[0]){
        for(int ui=0;ui<g_unitCount&&g_viewCount<MAX_UNITS;ui++)if(unit_matches(ui))g_view[g_viewCount++]=ui;
    }else{
        LONG ci=InterlockedCompareExchange(&g_cat,0,0);if(ci<0||ci>=g_catCount)ci=0;
        Category*c=&g_cats[ci];
        for(int i=0;i<c->count&&g_viewCount<MAX_UNITS;i++)g_view[g_viewCount++]=c->unitIndex[i];
    }
    LONG sc=InterlockedCompareExchange(&g_scroll,0,0);
    if(sc>g_viewCount-VISIBLE_ROWS)sc=g_viewCount>VISIBLE_ROWS?g_viewCount-VISIBLE_ROWS:0;
    if(sc<0)sc=0;
    InterlockedExchange(&g_scroll,sc);
}'''
pat = r'static int contains_fold\(.*?\nstatic void request_redraw'
s, n = re.subn(pat, new_search + '\nstatic void request_redraw', s, flags=re.S)
if n != 1:
    raise SystemExit(f'search replacement count={n}')

# Match the old INI defaults rather than RC10 hard-coded approximations.
s = s.replace('CreateFontW(-15,0,0,0,FW_NORMAL', 'CreateFontW(-ini_int(L"overlay_font_size",18),0,0,0,FW_NORMAL')
s = s.replace('CreateFontW(-15,0,0,0,FW_SEMIBOLD', 'CreateFontW(-ini_int(L"overlay_font_size",18),0,0,0,FW_SEMIBOLD')
s = s.replace('ini_int(L"overlay_alpha",238)', 'ini_int(L"overlay_alpha",230)')

# RC3 FIX1 bound only after live match + foreground, not during startup/menu stages.
s = s.replace('HWND h=NULL;if(foreground_candidate(&h))bind_game(h);Sleep(100);', 'HWND h=NULL;if(st==6&&foreground_candidate(&h))bind_game(h);Sleep(100);')

# Original interactive dropdown closes on a click in the game outside the overlay.
needle = 'static LRESULT CALLBACK game_proc(HWND h,UINT m,WPARAM w,LPARAM l){static int f12=0,ins=0;'
insert = needle + 'if(m==WM_LBUTTONDOWN&&InterlockedCompareExchange(&g_open,0,0)){InterlockedExchange(&g_open,0);InterlockedExchange(&g_searchActive,0);InterlockedExchange(&g_scroll,0);if(g_overlay){SetWindowPos(g_overlay,HWND_TOPMOST,0,0,OVERLAY_W,HEADER_H,SWP_NOMOVE|SWP_NOACTIVATE);InvalidateRect(g_overlay,NULL,FALSE);}logf0("P3O_DROPDOWN=CLOSE reason=game_click\\n");}'
if needle not in s:
    raise SystemExit('game_proc needle not found')
s = s.replace(needle, insert, 1)

# Make the log explicit about the recovered UI lineage.
s = s.replace('ONE_DLL=TRUE BACKEND_DLL=FALSE\\nWORLD=', 'ONE_DLL=TRUE BACKEND_DLL=FALSE\\nUI_LINEAGE=P3N_RC3_FIX1_RC4_RC5\\nWORLD=')

p.write_text(s, encoding='utf-8')
print('RC12 patch applied')
