import json
import time
import os
import base64
import requests
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

API_URL       = "https://api.mtjogos.co.ao/api/daily-lottery-results"
LIMIT_POR_PAG = 50
MAX_PAGINAS   = 30
ARQUIVO_JSON  = "historico_completo.json"
GITHUB_USER   = "Gabsapalo25"
GITHUB_REPO   = "kazola-dados"
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN")

ANGOLA_TZ = timezone(timedelta(hours=1))

HEADERS_GITHUB = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept":        "application/vnd.github.v3+json",
}


def purge_jsdelivr():
    url = f"https://purge.jsdelivr.net/gh/{GITHUB_USER}/{GITHUB_REPO}@main/{ARQUIVO_JSON}"
    try:
        r = requests.get(url, timeout=15)
        print("✅ jsDelivr cache limpo!" if r.status_code == 200
              else f"⚠️ jsDelivr purge: HTTP {r.status_code}")
    except Exception as e:
        print(f"⚠️ jsDelivr purge falhou: {e}")


def obter_sha_ficheiro():
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{ARQUIVO_JSON}"
    r = requests.get(url, headers=HEADERS_GITHUB, timeout=15)
    return r.json().get("sha") if r.status_code == 200 else None


def push_para_github(conteudo: str):
    sha = obter_sha_ficheiro()
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{ARQUIVO_JSON}"
    agora = datetime.now(ANGOLA_TZ).strftime("%Y-%m-%d %H:%M")
    payload = {
        "message": f"🔄 Auto-update {agora} Angola",
        "content": base64.b64encode(conteudo.encode("utf-8")).decode("utf-8"),
        "branch":  "main",
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=HEADERS_GITHUB, json=payload, timeout=30)
    if r.status_code in (200, 201):
        print("✅ Push para GitHub concluído!")
        return True
    print(f"❌ Erro no push: HTTP {r.status_code} — {r.text}")
    return False


def fetch_todos_os_registos() -> list:
    todos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "pt-AO,pt;q=0.9,en;q=0.8",
                "Referer":         "https://www.lotarianacional.co.ao/",
                "Origin":          "https://www.lotarianacional.co.ao",
            }
        )
        page = context.new_page()

        # Obter cookies reais visitando o site principal
        print("   🌐 Visitando site principal...")
        try:
            page.goto("https://www.lotarianacional.co.ao/", timeout=30000)
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"   ⚠️ Site principal inacessível: {e}")

        for pagina in range(1, MAX_PAGINAS + 1):
            url = f"{API_URL}?page={pagina}&limit={LIMIT_POR_PAG}"
            print(f"   📄 Página {pagina}...", flush=True)
            try:
                response = page.request.get(url, timeout=60000)
                print(f"   HTTP {response.status}")

                if response.status == 200:
                    registos = response.json().get('data', [])
                    if not registos:
                        print(f"   Página {pagina} vazia — fim")
                        break
                    todos.extend(registos)
                    print(f"   ✅ +{len(registos)} (total: {len(todos)})")
                    time.sleep(2)
                else:
                    print(f"   ❌ HTTP {response.status} — parando")
                    break
            except Exception as e:
                print(f"   ❌ Erro: {e}")
                break

        context.close()
        browser.close()

    return todos


def extrair():
    agora_angola = datetime.now(ANGOLA_TZ)
    print(f"[{agora_angola.strftime('%Y-%m-%d %H:%M:%S')} Angola] 🎲 Iniciando...")

    todos = fetch_todos_os_registos()

    if not todos:
        print("❌ Nenhum registo — saindo sem alterar ficheiro")
        return

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
        x.get('date', ''), x.get('session', '') or ''
    ), reverse=True)

    hoje = agora_angola.strftime("%Y-%m-%d")
    sorteios_hoje = sum(1 for i in sem_dup if i.get('date', '').startswith(hoje))
    print(f"✅ {len(sem_dup)} registos | hoje: {sorteios_hoje} sorteios")

    conteudo = json.dumps(sem_dup, indent=4, ensure_ascii=False)
    push_para_github(conteudo)
    purge_jsdelivr()


if __name__ == "__main__":
    extrair()
