from pydantic import BaseModel, Field, validator
from typing import List, Optional

class ChessMoveResponse(BaseModel):
    """Structured response from LLM for chess move selection."""
    selected_move: str = Field(..., description="The primary move selected by the LLM in UCI format (e.g., 'e2e4')")
    alternative_moves: List[str] = Field(default_factory=list, description="Alternative moves the LLM considered")
    reasoning: Optional[str] = Field(None, description="Reasoning behind the move selection")

    @validator('selected_move')
    def validate_selected_move(cls, v):
        # Basic UCI format validation (could be expanded)
        if not (len(v) == 4 or len(v) == 5):  # e2e4 or e7e8q for promotion
            raise ValueError(f"Invalid UCI move format: {v}")
        return v

    @validator('alternative_moves')
    def validate_alternative_moves(cls, v, values):
        # Ensure alternatives don't include the selected move
        if 'selected_move' in values and values['selected_move'] in v:
            v.remove(values['selected_move'])
        return v
