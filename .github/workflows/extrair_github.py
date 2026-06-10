import requests
import json
from datetime import datetime, timezone, timedelta

API_URL       = "https://api.mtjogos.co.ao/api/daily-lottery-results"
LIMIT_POR_PAG = 50
MAX_PAGINAS   = 30
ARQUIVO_JSON  = "historico_completo.json"
GITHUB_USER   = "Gabsapalo25"
GITHUB_REPO   = "kazola-dados"

# Angola = UTC+1
ANGOLA_TZ = timezone(timedelta(hours=1))

# Headers a simular browser real — necessário para contornar bloqueio 403 da API
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
    "Referer":         "https://www.lotarianacional.co.ao/",
    "Origin":          "https://www.lotarianacional.co.ao",
}

def purge_jsdelivr():
    url = f"https://purge.jsdelivr.net/gh/{GITHUB_USER}/{GITHUB_REPO}@main/{ARQUIVO_JSON}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            print("✅ jsDelivr cache limpo!")
        else:
            print(f"⚠️ jsDelivr purge: HTTP {r.status_code}")
    except Exception as e:
        print(f"⚠️ jsDelivr purge falhou: {e}")

def extrair():
    agora_angola = datetime.now(ANGOLA_TZ)
    print(f"[{agora_angola.strftime('%Y-%m-%d %H:%M:%S')} Angola] 🎲 Iniciando extracção...")

    todos = []
    pagina = 1

    while pagina <= MAX_PAGINAS:
        url = f"{API_URL}?page={pagina}&limit={LIMIT_POR_PAG}"
        try:
            print(f"   📄 Página {pagina}...", flush=True)
            r = requests.get(url, timeout=60, headers=HEADERS)

            if r.status_code != 200:
                print(f"   ⚠️ HTTP {r.status_code} — parando")
                break

            dados = r.json()
            registos = dados.get('data', [])

            if not registos:
                print(f"   📄 Página {pagina} vazia — parando")
                break

            todos.extend(registos)
            print(f"   ✅ +{len(registos)} (total: {len(todos)})")
            pagina += 1

        except Exception as e:
            print(f"   ❌ Erro: {e} — parando")
            break

    if not todos:
        print("❌ Nenhum registo obtido — API bloqueou ou está inacessível")
        return False

    # Remover duplicatas por data (1 registo = 1 dia)
    vistos = set()
    sem_dup = []
    for item in todos:
        uid = item.get('date', '')[:10]
        if uid and uid not in vistos:
            vistos.add(uid)
            sem_dup.append(item)

    sem_dup.sort(key=lambda x: x.get('date', ''), reverse=True)

    with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
        json.dump(sem_dup, f, indent=4, ensure_ascii=False)

    # Contar sorteios de hoje em hora Angola
    hoje = agora_angola.strftime("%Y-%m-%d")
    sorteios_hoje = sum(
        len(item.get('results', []))
        for item in sem_dup
        if item.get('date', '').startswith(hoje)
    )

    print(f"✅ {len(sem_dup)} registos guardados | hoje ({hoje}): {sorteios_hoje} sorteios")

    # Limpar cache CDN
    purge_jsdelivr()

    return True

if __name__ == "__main__":
    extrair()
