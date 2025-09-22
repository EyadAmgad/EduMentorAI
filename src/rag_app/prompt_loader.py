"""
Prompt loader utility for EduMentorAI
Loads prompts from YAML files for consistent prompt management
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path

class PromptLoader:
    """Utility class to load and manage prompts from YAML files"""
    
    def __init__(self):
        self.prompts_dir = Path(__file__).parent / 'prompts'
        self._cache = {}
    
    def load_prompts(self, filename: str = 'system_prompts.yaml') -> Dict[str, Any]:
        """
        Load prompts from YAML file
        
        Args:
            filename: Name of the YAML file to load
            
        Returns:
            Dictionary containing all prompts
        """
        if filename in self._cache:
            return self._cache[filename]
        
        file_path = self.prompts_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                prompts = yaml.safe_load(file)
                self._cache[filename] = prompts
                return prompts
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file {filename}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading prompt file {filename}: {e}")
    
    def get_prompt(self, prompt_key: str, filename: str = 'system_prompts.yaml') -> str:
        """
        Get a specific prompt by key
        
        Args:
            prompt_key: Dot-separated key to the prompt (e.g., 'slide_generation.main_prompt')
            filename: YAML file to load from
            
        Returns:
            The prompt string
        """
        prompts = self.load_prompts(filename)
        
        # Handle nested keys
        keys = prompt_key.split('.')
        current = prompts
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise KeyError(f"Prompt key '{prompt_key}' not found in {filename}")
        
        if not isinstance(current, str):
            raise ValueError(f"Prompt key '{prompt_key}' does not point to a string value")
        
        return current
    
    def format_prompt(self, prompt_key: str, **kwargs) -> str:
        """
        Get and format a prompt with provided variables
        
        Args:
            prompt_key: Dot-separated key to the prompt
            **kwargs: Variables to format into the prompt
            
        Returns:
            Formatted prompt string
        """
        prompt = self.get_prompt(prompt_key)
        return prompt.format(**kwargs)
    
    def clear_cache(self):
        """Clear the prompt cache"""
        self._cache.clear()


# Global instance for easy access
prompt_loader = PromptLoader()