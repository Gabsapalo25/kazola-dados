import requests
import json
import time
import os
import base64
from datetime import datetime, timezone, timedelta

API_URL       = "https://api.mtjogos.co.ao/api/daily-lottery-results"
LIMIT_POR_PAG = 50
MAX_PAGINAS   = 30
ARQUIVO_JSON  = "historico_completo.json"
GITHUB_USER   = "Gabsapalo25"
GITHUB_REPO   = "kazola-dados"
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN")

ANGOLA_TZ = timezone(timedelta(hours=1))

HEADERS_API = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "pt-AO,pt;q=0.9,en;q=0.8",
    "Referer":         "https://www.lotarianacional.co.ao/",
    "Origin":          "https://www.lotarianacional.co.ao",
}

HEADERS_GITHUB = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept":        "application/vnd.github.v3+json",
}


def purge_jsdelivr():
    url = (
        f"https://purge.jsdelivr.net/gh/{GITHUB_USER}/"
        f"{GITHUB_REPO}@main/{ARQUIVO_JSON}"
    )
    try:
        r = requests.get(url, timeout=15)
        print("✅ jsDelivr cache limpo!" if r.status_code == 200
              else f"⚠️ jsDelivr purge: HTTP {r.status_code}")
    except Exception as e:
        print(f"⚠️ jsDelivr purge falhou: {e}")


def obter_sha_ficheiro():
    url = (
        f"https://api.github.com/repos/{GITHUB_USER}/"
        f"{GITHUB_REPO}/contents/{ARQUIVO_JSON}"
    )
    r = requests.get(url, headers=HEADERS_GITHUB, timeout=15)
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def push_para_github(conteudo: str):
    sha = obter_sha_ficheiro()
    url = (
        f"https://api.github.com/repos/{GITHUB_USER}/"
        f"{GITHUB_REPO}/contents/{ARQUIVO_JSON}"
    )
    agora = datetime.now(ANGOLA_TZ).strftime("%Y-%m-%d %H:%M")
    payload = {
        "message": f"🔄 Auto-update {agora} Angola",
        "content": base64.b64encode(conteudo.encode("utf-8")).decode("utf-8"),
        "branch":  "main",
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=HEADERS_GITHUB,
                     json=payload, timeout=30)
    if r.status_code in (200, 201):
        print("✅ Push para GitHub concluído!")
        return True
    else:
        print(f"❌ Erro no push: HTTP {r.status_code} — {r.text}")
        return False


def fetch_pagina(pagina: int) -> list:
    url = f"{API_URL}?page={pagina}&limit={LIMIT_POR_PAG}"
    for tentativa in range(1, 4):
        try:
            if tentativa > 1:
                time.sleep(tentativa * 3)
            r = requests.get(url, timeout=60, headers=HEADERS_API)
            print(f"   Página {pagina} — HTTP {r.status_code}")
            if r.status_code == 200:
                return r.json().get('data', [])
            elif r.status_code == 403:
                print("   ⚠️ 403 — aguardando...")
                time.sleep(10)
            else:
                return None
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            time.sleep(5)
    return None


def extrair():
    agora_angola = datetime.now(ANGOLA_TZ)
    print(f"[{agora_angola.strftime('%Y-%m-%d %H:%M:%S')} Angola] 🎲 Iniciando...")

    todos = []
    pagina = 1

    while pagina <= MAX_PAGINAS:
        registos = fetch_pagina(pagina)
        if registos is None:
            break
        if not registos:
            print(f"   Página {pagina} vazia — fim")
            break
        todos.extend(registos)
        print(f"   ✅ +{len(registos)} (total: {len(todos)})")
        time.sleep(2)
        pagina += 1

    if not todos:
        print("❌ Nenhum registo — API inacessível")
        return

    # Remover duplicatas
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

    conteudo = json.dumps(sem_dup, indent=4, ensure_ascii=False)

    hoje = agora_angola.strftime("%Y-%m-%d")
    sorteios_hoje = sum(
        1 for item in sem_dup
        if item.get('date', '').startswith(hoje)
    )
    print(f"✅ {len(sem_dup)} registos | hoje: {sorteios_hoje} sorteios")

    push_para_github(conteudo)
    purge_jsdelivr()


# Loop infinito — corre de hora a hora
if __name__ == "__main__":
    while True:
        try:
            extrair()
        except Exception as e:
            print(f"❌ Erro geral: {e}")
        print("⏳ Aguardando 60 minutos...")
        time.sleep(3600)
