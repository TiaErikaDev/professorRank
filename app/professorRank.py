import os
os.environ['WDM_SSL_VERIFY'] = '0' 
import tkinter as tk
from tkinter import messagebox, scrolledtext
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time, tempfile

# Função principal que será chamada ao clicar no botão "Iniciar Consulta"
def iniciar_consulta():
    cpf = entry_cpf.get()
    senha = entry_senha.get()
    classificacao = entry_classificacao.get()
    crede = entry_crede.get()

    # Validação dos campos
    if not cpf or not senha or not classificacao:
        messagebox.showerror("Erro", "Preencha todos os campos!")
        return
    if not cpf.isdigit() or not classificacao.isdigit():
        messagebox.showerror("Erro", "CPF e classificação devem conter apenas números.")
        return

    # Limpa a área de resultados antes de iniciar uma nova consulta
    resultado_text.delete(1.0, tk.END)
    
    aguarde_label.config(text="Processando... Aguarde!")
    janela.update()

    # Configuração do Chrome em modo headless
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    user_data_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    driver.get("https://selecaoprofessor.seduc.ce.gov.br/login")
    time.sleep(2)

    WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, "cpf")))
    driver.find_element(By.ID, "cpf").send_keys(cpf)
    driver.find_element(By.ID, "pass").send_keys(senha)
    driver.find_element(By.ID, "btLogin").click()
    time.sleep(2)
    
    crede = crede.split()[-1]
    driver.get(f"https://selecaoprofessor.seduc.ce.gov.br/chamada_selecao?crede={crede}")
    time.sleep(2)
    
    select_munic = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="munic"]')))
    municipios = select_munic.find_elements(By.TAG_NAME, 'option')
    municipios_codigo = [munic.get_attribute("value") for munic in municipios]
    for munic_value in municipios_codigo:
        try:
            if not munic_value:  # Ignora a opção "---Selecione---"
                continue
            
            URL_CREDE = f"https://selecaoprofessor.seduc.ce.gov.br/chamada_selecao?crede={crede}&munic={munic_value}"
            driver.get(URL_CREDE)
            time.sleep(1)

            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr")))

            lista_escolas = driver.find_elements(By.XPATH, "//a[contains(@onclick, 'prepare_exibir_inscritos_carencia')]")
            
            if not lista_escolas:  # Se nenhuma escola for encontrada, passa para o próximo município
                resultado_text.insert(tk.END, f"Nenhuma escola encontrada no município {munic_value.text}. Passando para o próximo...\n")
                continue
            
            crede_name_credes = driver.find_element(By.XPATH, '//*[@id="container-body"]/div[1]/div/div/fieldset[2]/form/div[2]/div/button/span[1]').text
            crede_name_sefor = {
                21: "SEFOR 1",
                22: "SEFOR 2",
                23: "SEFOR 3"
            }
            crede_name = crede_name_sefor.get(int(crede), crede_name_credes)
            
            
            resultado_text.insert(tk.END, "\n")
            resultado_text.insert(tk.END, f"--------------------------------{crede_name}--------------------------------\n")
            resultado_text.insert(tk.END, f"Total de escolas na {crede_name}: {len(lista_escolas)}\n")
            
            for escola_index in range(len(lista_escolas)):
                try:
                    driver.get(URL_CREDE)
                    time.sleep(2)
                    escolas = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@onclick, 'prepare_exibir_inscritos_carencia')]"))
                    )
                    
                    nome_escola = driver.find_element(By.XPATH, f'//*[@id="container-body"]/div[1]/div/div/table/tbody/tr[{escola_index + 1}]/td[2]').text.split()
                    nome_formatado = " ".join(nome_escola[nome_escola.index('-') + 1:])
                    
                    resultado_text.insert(tk.END, f"Processando escola {escola_index + 1}: {nome_formatado}\n")    
                    
                    escolas[escola_index].click()  
                    time.sleep(1)  
                    
                    tabela = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.XPATH, '//*[@id="modal-inscritos"]/div/div/div[2]/table/tbody/tr'))
                    )

                    count = 0  # Reinicia o contador para cada escola
                    for linha in tabela:
                        try:
                            colunas = linha.find_elements(By.TAG_NAME, 'td')  
                            
                            if len(colunas) >= 5:
                                posicao_candidato = colunas[4].text.strip()
                                
                                if posicao_candidato.isdigit() and int(posicao_candidato) < int(classificacao):
                                    count += 1  # Incrementa apenas se a posição do candidato for menor que a sua

                        except Exception as e:
                            resultado_text.insert(tk.END, f"Erro ao processar linha: {e}\n")

                    # Fechar o modal após processar todas as linhas
                    fechar_botao = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Fechar")]')))
                    fechar_botao.click()
                    time.sleep(1)
                    
                    resultado_text.insert(tk.END, f'Total de candidatos: {len(tabela)}\n')

                    minha_colocacao = count + 1  # Sua classificação é o número de candidatos à frente + 1
                    if minha_colocacao <= 3:
                        resultado_text.insert(tk.END, f"Sua classificação na escola {escola_index + 1}: {minha_colocacao}º lugar ✅ ✅ ✅\n")
                    else:
                        resultado_text.insert(tk.END, f"Sua classificação na escola {escola_index + 1}: {minha_colocacao}º lugar\n")
                    resultado_text.insert(tk.END, "\n-----------------------------------------------------------------------\n\n")
                    
                except Exception as e:
                    resultado_text.insert(tk.END, f"Erro ao processar escola {escola_index + 1}: {e}\n")
                    driver.get(URL_CREDE)
                    time.sleep(1)
                            
        except Exception as e:
            continue

    driver.quit()
    resultado_text.insert(tk.END, "Consulta concluída!\n")

# Cria a janela da interface gráfica
janela = tk.Tk()
janela.title("ProfessorRank")

# Campos de entrada
tk.Label(janela, text="CPF:").grid(row=0, column=0)
entry_cpf = tk.Entry(janela)
entry_cpf.grid(row=0, column=1)

tk.Label(janela, text="Senha:").grid(row=1, column=0)
entry_senha = tk.Entry(janela, show="*")
entry_senha.grid(row=1, column=1)

tk.Label(janela, text="Classificação:").grid(row=2, column=0)
entry_classificacao = tk.Entry(janela)
entry_classificacao.grid(row=2, column=1)

tk.Label(janela, text="CREDE:").grid(row=3, column=0)
entry_crede = tk.Entry(janela)
entry_crede.grid(row=3, column=1)

# Botão para iniciar a consulta
tk.Button(janela, text="Iniciar Consulta", command=iniciar_consulta).grid(row=4, column=0, columnspan=2)

# Área de resultados (usando ScrolledText para permitir rolagem)
resultado_text = scrolledtext.ScrolledText(janela, width=100, height=40, wrap=tk.WORD)
resultado_text.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

# Label para exibir a mensagem de "Aguarde"
aguarde_label = tk.Label(janela, text="", fg="white", bg="black")
aguarde_label.grid(row=6, column=0, columnspan=2)

# Inicia a interface
janela.mainloop()