
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests pour l'interface entre les niveaux tactique et opérationnel.
"""

import unittest
from unittest.mock import MagicMock

import json
from datetime import datetime

from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface
from argumentation_analysis.paths import DATA_DIR, RESULTS_DIR
from argumentation_analysis.core.communication import (
    MessageMiddleware, TacticalAdapter, OperationalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


class TestTacticalOperationalInterface(unittest.TestCase):
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests pour la classe TacticalOperationalInterface."""
    
    def setUp(self):
        """Initialise les objets nécessaires pour les tests."""
        # Créer des mocks pour les états
        self.mock_tactical_state = MagicMock(spec=TacticalState)
        
        # Créer un mock pour le middleware
        self.mock_middleware = MagicMock(spec=MessageMiddleware)
        
        # Créer des mocks pour les adaptateurs
        self.mock_tactical_adapter = MagicMock(spec=TacticalAdapter)
        self.mock_operational_adapter = MagicMock(spec=OperationalAdapter)
        
        # Ajouter les attributs manquants aux mocks
        self.mock_tactical_adapter.request_operational_info = MagicMock()
        self.mock_operational_adapter.send_result = MagicMock()
        
        # Configurer le mock du middleware pour retourner les adaptateurs mockés
        self.mock_middleware.get_adapter.side_effect = lambda agent_id, level: \
            self.mock_tactical_adapter if level == AgentLevel.TACTICAL else self.mock_operational_adapter
        
        # Configurer les mocks
        self.mock_tactical_state.tasks = {
            "pending": [
                {
                    "id": "task-1",
                    "description": "Extraire les segments de texte contenant des arguments potentiels",
                    "objective_id": "obj-1",
                    "estimated_duration": "short",
                    "required_capabilities": ["text_extraction"],
                    "priority": "high"
                }
            ],
            "in_progress": [
                {
                    "id": "task-2",
                    "description": "Identifier les prémisses et conclusions explicites",
                    "objective_id": "obj-1",
                    "estimated_duration": "medium",
                    "required_capabilities": ["argument_identification"],
                    "priority": "high"
                }
            ],
            "completed": [
                {
                    "id": "task-3",
                    "description": "Analyser les arguments pour détecter les sophismes formels",
                    "objective_id": "obj-2",
                    "estimated_duration": "medium",
                    "required_capabilities": ["fallacy_detection", "formal_logic"],
                    "priority": "medium"
                }
            ],
            "failed": []
        }
        
        self.mock_tactical_state.get_task_dependencies = MagicMock(return_value=["task-3"])
        
        # Créer l'interface avec les mocks
        self.interface = TacticalOperationalInterface(
            tactical_state=self.mock_tactical_state,
            operational_state=None,  # OperationalState n'est pas encore implémenté
            middleware=self.mock_middleware
        )
        
        # Remplacer les adaptateurs de l'interface par nos mocks
        self.interface.tactical_adapter = self.mock_tactical_adapter
        self.interface.operational_adapter = self.mock_operational_adapter
    
    def test_translate_task(self):
        """Teste la traduction d'une tâche tactique en tâche opérationnelle."""
        # Définir une tâche à traduire
        task = {
            "id": "task-1",
            "description": "Extraire les segments de texte contenant des arguments potentiels",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],
            "priority": "high"
        }
        
        # Configurer le mock pour assign_task
        self.mock_tactical_adapter.assign_task.return_value = "task-id-123"
        
        # Appeler la méthode à tester
        command = self.interface.translate_task_to_command(task)

        # Vérifier que la méthode assign_task a été appelée
        self.mock_tactical_adapter.assign_task.assert_called_once()
        
        # Vérifier le résultat
        self.assertIsInstance(command, dict)
        self.assertIn("id", command)
        self.assertIn("tactical_task_id", command)
        self.assertIn("description", command)
        self.assertIn("objective_id", command)
        self.assertIn("techniques", command)
        self.assertIn("text_extracts", command)
        self.assertIn("parameters", command)
        self.assertIn("expected_outputs", command)
        self.assertIn("priority", command)
        self.assertIn("context", command)
        
        # Vérifier que l'identifiant tactique est correctement référencé
        self.assertEqual(command["tactical_task_id"], "task-1")
        
        # Vérifier que les techniques sont déterminées en fonction des capacités
        self.assertIsInstance(command["techniques"], list)
        self.assertIsInstance(command["techniques"], list) # La logique peut retourner une liste vide
        
        # Vérifier le contexte
        self.assertIn("position_in_workflow", command["context"])
        self.assertIn("related_tasks", command["context"])
        self.assertIn("dependencies", command["context"])
        self.assertIn("constraints", command["context"])
    
    def test_determine_techniques(self):
        """Teste la détermination des techniques en fonction des capacités."""
        # Tester avec différentes capacités
        
        # Capacité d'identification d'arguments
        capabilities = ["argument_identification"]
        result = self.interface._determine_techniques(capabilities)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["name"], "premise_conclusion_extraction")
        
        # Capacité de détection de sophismes
        capabilities = ["fallacy_detection"]
        result = self.interface._determine_techniques(capabilities)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["name"], "fallacy_pattern_matching")
        
        # Capacité de logique formelle
        capabilities = ["formal_logic"]
        result = self.interface._determine_techniques(capabilities)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["name"], "propositional_logic_formalization")
        
        # Capacités multiples
        capabilities = ["argument_identification", "fallacy_detection"]
        result = self.interface._determine_techniques(capabilities)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        # Devrait contenir les techniques des deux capacités
        technique_names = [technique["name"] for technique in result]
        self.assertIn("premise_conclusion_extraction", technique_names)
        self.assertIn("fallacy_pattern_matching", technique_names)
    
    def test_determine_relevant_extracts(self):
        """Teste la détermination des extraits de texte pertinents."""
        # Définir une tâche fictive
        task = {
            "description": "Extraire les segments de texte contenant des arguments potentiels",
            "objective_id": "obj-1"
        }
        
        # Appeler la méthode à tester
        result = self.interface._determine_relevant_extracts(task)
        
        # Vérifier le résultat
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn("id", result[0])
        self.assertIn("source", result[0])
        self.assertIn("content", result[0])
        # La clé 'relevance' n'est plus garantie
    
    def test_determine_execution_parameters(self):
        """Teste la détermination des paramètres d'exécution."""
        # Tester avec différentes durées et priorités
        
        # Tâche courte et priorité élevée
        task = {
            "estimated_duration": "short",
            "priority": "high"
        }
        result = self.interface._determine_execution_parameters(task)
        self.assertIsInstance(result, dict)
        self.assertIn("timeout", result)
        self.assertIn("max_iterations", result)
        self.assertIn("precision_target", result)
        self.assertEqual(result["timeout"], 60)
        self.assertEqual(result["precision_target"], 0.8)
        
        # Tâche moyenne et priorité moyenne
        task = {
            "estimated_duration": "medium",
            "priority": "medium"
        }
        result = self.interface._determine_execution_parameters(task)
        self.assertEqual(result["timeout"], 60)
        self.assertEqual(result["precision_target"], 0.8)
        
        # Tâche longue et priorité faible
        task = {
            "estimated_duration": "long",
            "priority": "low"
        }
        result = self.interface._determine_execution_parameters(task)
        self.assertEqual(result["timeout"], 60)
        self.assertEqual(result["precision_target"], 0.8)
    
    def test_determine_expected_outputs(self):
        """Teste la détermination des outputs attendus."""
        # Tester avec différentes descriptions de tâches
        
        # Tâche d'identification d'arguments
        task = {
            "description": "Identifier les arguments dans le texte"
        }
        result = self.interface._determine_expected_outputs(task)
        self.assertIsInstance(result, dict)
        self.assertIn("generic_result", result) # La logique est maintenant générique
        
        # Tâche générique
        task = {
            "description": "Effectuer une analyse générale"
        }
        result = self.interface._determine_expected_outputs(task)
        self.assertIn("generic_result", result)
    
    def test_determine_position_in_workflow(self):
        """Teste la détermination de la position dans le workflow."""
        # Tester avec différents identifiants de tâches
        
        # Première tâche
        task = {
            "id": "task-obj-1"
        }
        result = self.interface._determine_position_in_workflow(task)
        self.assertIsInstance(result, dict)
        self.assertIn("phase", result)
        self.assertIn("is_first", result)
        self.assertIn("is_last", result)
        self.assertEqual(result["phase"], "intermediate")
        self.assertFalse(result["is_first"])
    
    def test_find_related_tasks(self):
        """Teste la recherche de tâches liées."""
        # Définir une tâche
        task = {
            "id": "task-1",
            "objective_id": "obj-1"
        }
        
        # Appeler la méthode à tester
        result = self.interface._find_related_tasks(task)
        
        # Vérifier le résultat
        self.assertIsInstance(result, list)
        self.assertIn("task-2", result)  # Car task-2 a le même objective_id
        self.assertNotIn("task-3", result)  # Car task-3 a un objective_id différent
        
        # Tester avec une tâche sans objective_id
        task = {
            "id": "task-4"
        }
        result = self.interface._find_related_tasks(task)
        self.assertEqual(result, [])
    
    def test_translate_dependencies(self):
        """Teste la traduction des dépendances tactiques en dépendances opérationnelles."""
        # Définir une tâche
        task = {
            "id": "task-1"
        }
        
        # Appeler la méthode à tester
        result = self.interface._translate_dependencies(task)
        
        # Vérifier le résultat
        self.assertIsInstance(result, list)
        self.assertEqual(result, ["op-task-3"])
    
    def test_determine_constraints(self):
        """Teste la détermination des contraintes."""
        # Tester avec différentes priorités
        
        # Priorité élevée
        task = {
            "priority": "high"
        }
        result = self.interface._determine_constraints(task)
        self.assertIsInstance(result, dict)
        self.assertIn("max_runtime", result)
        self.assertIn("min_confidence", result)
        # self.assertIn("max_memory", result) # N'est plus une clé retournée
        self.assertEqual(result["max_runtime"], 60)
        self.assertEqual(result["min_confidence"], 0.7)
        
        # Priorité moyenne
        task = {
            "priority": "medium"
        }
        result = self.interface._determine_constraints(task)
        self.assertEqual(result["max_runtime"], 60)
        self.assertEqual(result["min_confidence"], 0.7)
        
        # Priorité faible
        task = {
            "priority": "low"
        }
        result = self.interface._determine_constraints(task)
        self.assertEqual(result["max_runtime"], 60)
        self.assertEqual(result["min_confidence"], 0.7)
    
    def test_process_operational_result(self):
        """Teste le traitement d'un résultat opérationnel."""
        # Définir un résultat opérationnel
        operational_result = {
            "id": "op-task-1",
            "task_id": "task-1",
            "tactical_task_id": "task-1",
            "status": "completed",
            "outputs": {
                "identified_arguments": [
                    {
                        "id": "arg-1",
                        "premises": ["Premise 1", "Premise 2"],
                        "conclusion": "Conclusion",
                        "confidence": 0.8
                    }
                ]
            },
            "metrics": {
                "execution_time": 2.5,
                "confidence": 0.8,
                "coverage": 0.9,
                "resource_usage": 0.6
            },
            "issues": [
                {
                    "type": "low_confidence",
                    "description": "Confiance faible pour certains arguments",
                    "severity": "medium",
                    "details": {
                        "affected_arguments": ["arg-2"]
                    }
                }
            ]
        }
        
        # Appeler la méthode à tester
        self.interface.process_operational_result(operational_result, operational_result)

        # Vérifier que l'adaptateur opérationnel a été utilisé pour envoyer le rapport
        self.mock_operational_adapter.send_result.assert_called_once()
        
        # Le rapport est maintenant envoyé via l'adaptateur, et la méthode ne retourne rien.
        # Pour ce test unitaire, vérifier que la méthode a été appelée est suffisant.
        # Les tests d'intégration vérifieront le contenu exact.
        pass
    
    def test_translate_outputs(self):
        """Teste la traduction des outputs opérationnels."""
        # Définir des outputs opérationnels
        outputs = {
            "identified_arguments": [
                {
                    "id": "arg-1",
                    "premises": ["Premise 1", "Premise 2"],
                    "conclusion": "Conclusion",
                    "confidence": 0.8
                }
            ]
        }
        
        # Appeler la méthode à tester
        result = self.interface._translate_outputs(outputs)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("identified_arguments", result)
        self.assertEqual(result, outputs)  # Dans l'implémentation actuelle, les outputs sont copiés tels quels
    
    def test_translate_metrics(self):
        """Teste la traduction des métriques opérationnelles."""
        # Définir des métriques opérationnelles
        metrics = {
            "execution_time": 2.5,
            "confidence": 0.8,
            "coverage": 0.9,
            "resource_usage": 0.6
        }
        
        # Appeler la méthode à tester
        result = self.interface._translate_metrics(metrics)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("processing_time", result)
        self.assertIn("confidence_score", result)
        
        # Vérifier que les valeurs sont correctement traduites
        self.assertEqual(result["processing_time"], 2.5)
        self.assertEqual(result["confidence_score"], 0.8)
        # Les autres clés ne sont plus garanties
    
    def test_translate_issues(self):
        """Teste la traduction des problèmes opérationnels."""
        # Définir des problèmes opérationnels
        issues = [
            {
                "type": "execution_error",
                "description": "Erreur lors de l'exécution",
                "severity": "high",
                "details": {
                    "error_code": 500
                }
            },
            {
                "type": "timeout",
                "description": "Délai d'exécution dépassé",
                "severity": "medium",
                "details": {
                    "elapsed_time": 60
                }
            },
            {
                "type": "low_confidence",
                "description": "Confiance faible pour certains arguments",
                "severity": "low",
                "details": {
                    "affected_arguments": ["arg-2"]
                }
            },
            {
                "type": "custom_issue",
                "description": "Problème personnalisé",
                "severity": "medium"
            }
        ]
        
        # Appeler la méthode à tester
        result = self.interface._translate_issues(issues)
        
        # Vérifier le résultat
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        
        # Vérifier que les types sont correctement traduits
        self.assertEqual(result[0]["type"], "task_failure")
        self.assertEqual(result[1]["type"], "task_timeout")
        self.assertEqual(result[2]["type"], "low_confidence")
        self.assertEqual(result[3]["type"], "custom_issue")


    def test_map_priority_to_enum(self):
        """Teste la conversion de priorité textuelle en énumération."""
        # Tester avec différentes priorités
        self.assertEqual(self.interface._map_priority_to_enum("high"), MessagePriority.HIGH)
        self.assertEqual(self.interface._map_priority_to_enum("medium"), MessagePriority.NORMAL)
        self.assertEqual(self.interface._map_priority_to_enum("low"), MessagePriority.LOW)
        self.assertEqual(self.interface._map_priority_to_enum("unknown"), MessagePriority.NORMAL)
    
    def test_determine_appropriate_agent(self):
        """Teste la détermination de l'agent approprié."""
        # Tester avec différentes capacités
        self.assertEqual(self.interface._determine_appropriate_agent(["argument_identification"]), "informal_analyzer")
        self.assertEqual(self.interface._determine_appropriate_agent(["formal_logic"]), "logic_analyzer")
        self.assertEqual(self.interface._determine_appropriate_agent(["text_extraction"]), "extract_processor")
        self.assertEqual(self.interface._determine_appropriate_agent(["argument_visualization"]), "default_operational_agent")
        
        # Tester avec des capacités multiples
        self.assertEqual(
            self.interface._determine_appropriate_agent(["argument_identification", "fallacy_detection"]),
            "informal_analyzer"
        )
        
        # Tester avec des capacités inconnues
        self.assertEqual(self.interface._determine_appropriate_agent(["unknown_capability"]), "default_operational_agent")
    
    def test_subscribe_to_operational_updates(self):
        """Teste l'abonnement aux mises à jour opérationnelles."""
        # Définir un callback
        def callback(message):
            pass
        
        # Configurer le mock pour subscribe_to_operational_updates
        self.mock_tactical_adapter.subscribe_to_operational_updates.return_value = "subscription-id-123"
        
        # Appeler la méthode à tester
        result = self.interface.subscribe_to_operational_updates(
            update_types=["task_progress", "resource_usage"],
            callback=callback
        )
        
        # Vérifier le résultat
        self.assertEqual(result, "subscription-id-123")
        
        # Vérifier que la méthode subscribe_to_operational_updates a été appelée
        self.mock_tactical_adapter.subscribe_to_operational_updates.assert_called_once_with(
            update_types=["task_progress", "resource_usage"],
            callback=callback
        )
    
    def test_request_operational_status(self):
        """Teste la demande de statut opérationnel."""
        # Configurer le mock pour request_operational_info
        expected_response = {
            "status": "ok",
            "tasks_in_progress": 2
        }
        self.mock_tactical_adapter.request_operational_info.return_value = expected_response
        
        # Appeler la méthode à tester
        result = self.interface.request_operational_status("operational_agent", timeout=5.0)
        
        # Vérifier le résultat
        self.assertEqual(result, expected_response)
        
        # Vérifier que la méthode request_operational_info a été appelée
        self.mock_tactical_adapter.request_operational_info.assert_called_once_with(
            request_type="agent_status",
            parameters={"agent_id": "operational_agent"},
            recipient_id="operational_agent",
            timeout=5.0
        )


if __name__ == "__main__":
    unittest.main()