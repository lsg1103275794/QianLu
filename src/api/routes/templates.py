"""
API routes for managing and retrieving analysis prompt templates.
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import yaml # Add yaml import if needed
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from src.utils.logging import logger

# Define the base path for templates relative to the project root
TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent /"config/prompt_templates"

class TemplateInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    # Add other fields if templates have more metadata, e.g., version, tags

router = APIRouter(
    prefix="/api/templates",
    tags=["templates"],
)

def parse_template_file(file_path: Path) -> Optional[TemplateInfo]:
    """Parses a template file to extract basic information."""
    try:
        template_id = file_path.stem # Use filename without extension as ID
        content_str = file_path.read_text(encoding='utf-8')
        
        data: Dict[str, Any] = {}
        if file_path.suffix.lower() == '.json':
            data = json.loads(content_str)
        elif file_path.suffix.lower() in ['.yaml', '.yml']:
            data = yaml.safe_load(content_str)
        # Add logic for other formats if needed (e.g., parsing front matter from markdown)
        else:
             logger.warning(f"Skipping unsupported template file format: {file_path.name}")
             return None

        # Extract required fields - adjust keys based on your actual template structure
        name = data.get('name', template_id) # Use ID as fallback name
        description = data.get('description')
        
        return TemplateInfo(id=template_id, name=name, description=description)

    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from template file: {file_path.name}")
        return None
    except yaml.YAMLError:
         logger.error(f"Error decoding YAML from template file: {file_path.name}")
         return None
    except Exception as e:
        logger.error(f"Error parsing template file {file_path.name}: {e}", exc_info=True)
        return None

@router.get("", response_model=List[TemplateInfo], summary="List available analysis templates")
def list_templates():
    """
    Retrieves a list of available analysis prompt templates from the configuration directory.
    It assumes templates are JSON or YAML files and contain at least 'name' and optionally 'description'.
    The filename (without extension) is used as the template ID.
    """
    if not TEMPLATE_DIR.is_dir():
        logger.error(f"Template directory not found: {TEMPLATE_DIR}")
        # Return empty list instead of 500 error if dir doesn't exist
        # raise HTTPException(status_code=500, detail="Template directory configuration error.")
        return []

    templates: List[TemplateInfo] = []
    try:
        for item in TEMPLATE_DIR.iterdir():
            if item.is_file() and item.suffix.lower() in ['.json', '.yaml', '.yml']:
                template_info = parse_template_file(item)
                if template_info:
                    templates.append(template_info)
        
        # Sort templates by name for consistent ordering
        templates.sort(key=lambda t: t.name)
        logger.info(f"Found {len(templates)} valid analysis templates.")
        return templates
        
    except Exception as e:
        logger.error(f"Error listing templates from {TEMPLATE_DIR}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list templates.")

# Add other template-related routes here if needed (e.g., get template details by ID) 