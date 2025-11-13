import os
import argparse

def sort_file_and_rename(input_filename: str):
    """
    Lê um arquivo, ordena suas linhas e escreve o resultado em um novo arquivo
    chamado 'nome_original_ordered.ext'.
    """
    try:
        # 1. Preparar o nome do arquivo de saída
        base_name, extension = os.path.splitext(input_filename)
        output_filename = f"{base_name}_ordered{extension}"

        # 2. Ler e Ordenar
        with open(input_filename, 'r') as infile:
            # remove '\n' para garantir uma ordenação limpa, depois adiciona de volta
            lines = [line.strip() for line in infile]
        
        # Ordena as linhas alfabeticamente
        lines.sort() 
        
        # Adiciona a quebra de linha de volta para escrita
        sorted_lines = [line + '\n' for line in lines]
        
        # 3. Escrever no Novo Arquivo
        with open(output_filename, 'w') as outfile:
            outfile.writelines(sorted_lines)
        
        print(f"✅ Sucesso!")
        print(f"   Arquivo original: '{input_filename}'")
        print(f"   Resultado ordenado salvo em: '{output_filename}'")
        
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo de entrada '{input_filename}' não encontrado.")
    except Exception as e:
        print(f"❌ Ocorreu um erro inesperado: {e}")


if __name__ == "__main__":
    # Configura o argparse
    parser = argparse.ArgumentParser(
        description="Ordena as linhas de um arquivo de texto e salva o resultado em um novo arquivo com o sufixo '_ordered'."
    )
    
    # Adiciona o argumento posicional para o nome do arquivo
    parser.add_argument(
        "input_file", 
        type=str, 
        help="O nome do arquivo de texto a ser ordenado."
    )
    
    # Analisa os argumentos da linha de comando
    args = parser.parse_args()
    
    # Chama a função principal com o argumento fornecido
    sort_file_and_rename(args.input_file)