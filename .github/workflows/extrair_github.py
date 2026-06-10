import requests
import json
from datetime import datetime

API_URL = "https://api.mtjogos.co.ao/api/daily-lottery-results"
LIMIT_POR_PAG = 50
MAX_PAGINAS = 30
ARQUIVO_JSON = "historico_completo.json"

def extrair():
    print(f"[{datetime.now()}] 🎲 Iniciando extracção...")
    
    todos = []
    pagina = 1
    
    while pagina <= MAX_PAGINAS:
        url = f"{API_URL}?page={pagina}&limit={LIMIT_POR_PAG}"
        try:
            print(f"   📄 Página {pagina}...", flush=True)
            r = requests.get(url, timeout=60)
            
            if r.status_code != 200:
                print(f"   ⚠️ HTTP {r.status_code} - parando")
                break
            
            dados = r.json()
            registos = dados.get('data', [])
            
            if not registos:
                print(f"   📄 Página {pagina} vazia - parando")
                break
            
            todos.extend(registos)
            print(f"   ✅ +{len(registos)} (total: {len(todos)})")
            pagina += 1
            
        except Exception as e:
            print(f"   ❌ Erro: {e} - parando")
            break
    
    if not todos:
        print("❌ Nenhum registo obtido")
        return False
    
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
    
    hoje = datetime.now().strftime("%Y-%m-%d")
    sorteios_hoje = sum(
        len(item.get('results', []))
        for item in sem_dup
        if item.get('date', '').startswith(hoje)
    )
    
    print(f"✅ {len(sem_dup)} registos | hoje: {sorteios_hoje} sorteios")
    return True

if __name__ == "__main__":
    extrair()
