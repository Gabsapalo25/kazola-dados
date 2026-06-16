import requests
import json
import time
from datetime import datetime, timezone, timedelta

API_URL       = "https://api.mtjogos.co.ao/api/daily-lottery-results"
LIMIT_POR_PAG = 50
MAX_PAGINAS   = 30
ARQUIVO_JSON  = "historico_completo.json"
GITHUB_USER   = "Gabsapalo25"
GITHUB_REPO   = "kazola-dados"

ANGOLA_TZ = timezone(timedelta(hours=1))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-AO,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Referer": "https://www.lotarianacional.co.ao/",
    "Origin": "https://www.lotarianacional.co.ao",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}


def purge_jsdelivr():
    url = (
        f"https://purge.jsdelivr.net/gh/{GITHUB_USER}/"
        f"{GITHUB_REPO}@main/{ARQUIVO_JSON}"
    )
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            print("✅ jsDelivr cache limpo!")
        else:
            print(f"⚠️ jsDelivr purge: HTTP {r.status_code}")
    except Exception as e:
        print(f"⚠️ jsDelivr purge falhou: {e}")


def fetch_pagina(pagina: int, tentativas: int = 5) -> list:
    url = f"{API_URL}?page={pagina}&limit={LIMIT_POR_PAG}"
    for tentativa in range(1, tentativas + 1):
        try:
            print(f"   📄 Página {pagina} (tentativa {tentativa})...", flush=True)
            if tentativa > 1:
                time.sleep(tentativa * 3)
            r = requests.get(url, timeout=60, headers=HEADERS)
            print(f"   HTTP {r.status_code}")
            if r.status_code == 200:
                dados = r.json()
                return dados.get('data', [])
            elif r.status_code == 403:
                print(f"   ⚠️ 403 Forbidden — aguardando antes de retry...")
                time.sleep(10)
            else:
                print(f"   ⚠️ HTTP {r.status_code} — parando")
                return None
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            time.sleep(5)
    print(f"   ❌ Todas as tentativas falharam para página {pagina}")
    return None


def extrair():
    agora_angola = datetime.now(ANGOLA_TZ)
    print(
        f"[{agora_angola.strftime('%Y-%m-%d %H:%M:%S')} Angola] "
        f"🎲 Iniciando extracção..."
    )

    todos = []
    pagina = 1

    while pagina <= MAX_PAGINAS:
        registos = fetch_pagina(pagina)

        if registos is None:
            print("   🛑 Parando paginação por erro definitivo")
            break

        if not registos:
            print(f"   📄 Página {pagina} vazia — fim dos dados")
            break

        todos.extend(registos)
        print(f"   ✅ +{len(registos)} (total acumulado: {len(todos)})")

        time.sleep(2)
        pagina += 1

    if not todos:
        print("❌ Nenhum registo obtido — saindo sem alterar o ficheiro")
        return False

    vistos = set()
    sem_dup = []
    for item in todos:
        data   = item.get('date', '')[:10]
        sessao = item.get('session', '') or item.get('type', '') or ''
        uid    = f"{data}_{sessao}"
        if uid and uid not in vistos:
            vistos.add(uid)
            sem_dup.append(item)

    sem_dup.sort(key=lambda x: (
        x.get('date', ''),
        x.get('session', '') or ''
    ), reverse=True)

    with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
        json.dump(sem_dup, f, indent=4, ensure_ascii=False)

    hoje = agora_angola.strftime("%Y-%m-%d")
    sorteios_hoje = sum(
        1 for item in sem_dup
        if item.get('date', '').startswith(hoje)
    )

    print(
        f"✅ {len(sem_dup)} registos guardados | "
        f"hoje ({hoje}): {sorteios_hoje} sorteios"
    )

    purge_jsdelivr()
    return True


if __name__ == "__main__":
    extrair()
