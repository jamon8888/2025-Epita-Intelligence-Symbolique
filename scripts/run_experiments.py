import subprocess
import re
import os
import sys

import logging

# Configuration du logging
log_file_path = 'logs/experiments.log'
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
def run_experiments():
    """
    Lance une série d'expériences en variant les agents et les taxonomies,
    capture les scores de précision et génère un rapport Markdown.
    """
    agents = ["simple", "workflow_only", "explore_only", "full"]
    taxonomies = ["taxonomy_small.csv", "taxonomy_medium.csv", "taxonomy_full.csv"]
    taxonomy_base_path = "argumentation_analysis/data/"
    validation_script_path = "demos/validation_complete_epita.py"

    results = {agent: {} for agent in agents}

    print("Début des expériences...")

    for agent in agents:
        for taxonomy_file in taxonomies:
            taxonomy_path = os.path.join(taxonomy_base_path, taxonomy_file)
            taxonomy_name = taxonomy_file.replace('.csv', '').replace('taxonomy_', '')

            logging.info(f"Exécution : Agent='{agent}', Taxonomie='{taxonomy_name}'...")

            command = [
                sys.executable,
                validation_script_path,
                "--agent-type",
                agent,
                "--taxonomy",
                taxonomy_path,
                "--verbose"
            ]
            
            try:
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                
                output = process.stdout
                
                logging.info(f"--- STDOUT de {agent}/{taxonomy_name} ---")
                logging.info(output)
                logging.info(f"--- Fin STDOUT ---")
                
                if process.returncode != 0:
                    logging.error(f"  -> Erreur (code {process.returncode}):")
                    logging.error(f"--- STDERR de {agent}/{taxonomy_name} ---")
                    logging.error(process.stderr)
                    logging.error(f"--- Fin STDERR ---")
                    results[agent][taxonomy_name] = "Erreur"
                    continue
                
                # Expression régulière pour trouver le score de précision final
                # Regex mise à jour pour correspondre au format de sortie "[TARGET] SCORE FINAL: ... (XX.X%)"
                match = re.search(r"SCORE FINAL:.*?\((\d+\.\d+)%\)", output)
                
                if match:
                    score = float(match.group(1))
                    results[agent][taxonomy_name] = f"{score:.2f}%"
                    logging.info(f"  -> Score trouvé : {score:.2f}%")
                else:
                    results[agent][taxonomy_name] = "N/A"
                    logging.warning("  -> Score non trouvé dans la sortie.")

            except subprocess.CalledProcessError as e:
                logging.error(f"  -> Erreur lors de l'exécution pour Agent='{agent}', Taxonomie='{taxonomy_name}':")
                logging.error(e.stderr)
                results[agent][taxonomy_name] = "Erreur"
            except FileNotFoundError:
                logging.error(f"Erreur: Le script '{validation_script_path}' est introuvable.")
                return
                print(f"Erreur: Le script '{validation_script_path}' est introuvable.")
                return

    logging.info("\nExpériences terminées.\n")
    generate_markdown_report(results, taxonomies)

def generate_markdown_report(results, taxonomies):
    """
    Génère et affiche un tableau Markdown à partir des résultats des expériences.
    """
    header = "| Agent          | " + " | ".join([t.replace('.csv', '').replace('taxonomy_', '').capitalize() for t in taxonomies]) + " |"
    separator = "|----------------|-" + "-|-".join(["-" * len(t.replace('.csv', '').replace('taxonomy_', '')) for t in taxonomies]) + "-|"
    
    logging.info("Tableau des résultats :")
    logging.info(header)
    logging.info(separator)

    for agent, scores in results.items():
        row = f"| {agent:<14} |"
        for taxonomy_file in taxonomies:
            taxonomy_name = taxonomy_file.replace('.csv', '').replace('taxonomy_', '')
            score = scores.get(taxonomy_name, "N/A")
            row += f" {score:<{len(taxonomy_name)}} |"
        logging.info(row)

if __name__ == "__main__":
    run_experiments()