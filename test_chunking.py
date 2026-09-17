import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from engine.extractor import extract_schema, chunk_markdown, merge_json_outputs

@pytest.mark.asyncio
async def test_chunking_and_merging():
    # 1. Test chunk_markdown
    large_markdown = "A" * 30000
    chunks = chunk_markdown(large_markdown, chunk_size=12000, overlap=1000)
    assert len(chunks) == 3
    assert len(chunks[0]) == 12000
    
    # 2. Test merge_json_outputs
    chunk1_result = {
        "temple_name": "Test Temple",
        "poojas": [{"name": "Puja A"}, {"name": "Puja B"}],
        "rituals": [],
        "products_sold": []
    }
    chunk2_result = {
        "temple_name": "", # Should be ignored because first chunk has it
        "poojas": [{"name": "Puja B"}, {"name": "Puja C"}], # B is duplicate
        "rituals": [{"name": "Ritual X"}],
        "products_sold": []
    }
    merged = merge_json_outputs([chunk1_result, chunk2_result])
    
    assert merged["temple_name"] == "Test Temple"
    assert len(merged["poojas"]) == 3
    assert merged["poojas"] == [{"name": "Puja A"}, {"name": "Puja B"}, {"name": "Puja C"}]
    assert merged["rituals"] == [{"name": "Ritual X"}]
    
    # 3. Test extract_schema with mock
    schema = {"type": "object", "properties": {"temple_name": {"type": "string"}}}
    with patch('engine.extractor._extract_chunk', new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = [chunk1_result, chunk2_result, None]
        
        # Test with OpenRouter mock flag so it doesn't fail on missing keys
        with patch('engine.extractor.settings.OPENROUTER_API_KEY', 'test_key'):
            with patch('engine.extractor.settings.GROQ_API_KEY', ''):
                result = await extract_schema(large_markdown, schema)
                assert result is not None
                assert result["temple_name"] == "Test Temple"
                assert len(result["poojas"]) == 3
                assert mock_extract.call_count == 3
