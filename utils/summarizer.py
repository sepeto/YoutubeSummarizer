import os
import logging
import openai
from typing import Dict, List
from dotenv import load_dotenv

class Summarizer:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Load summary prompt
        with open('summary_prompt.txt', 'r', encoding='utf-8') as f:
            self.summary_prompt = f.read()
        
    async def generate_summary(self, text: str, transcript_filename: str) -> str:
        """Generate a summary from text."""
        try:
            # Generate summary using OpenAI API
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.summary_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            summary = response.choices[0].message.content
            
            # Save summary using original filename
            if summary:
                filename = self._get_filename(transcript_filename)
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(summary)
                self.logger.info(f"Summary saved to {filename}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {str(e)}")
            return None
        
    def _get_filename(self, transcript_filename: str) -> str:
        """Generate summary filename from transcript filename."""
        # Remove .txt and add _summary.txt
        base_name = os.path.splitext(transcript_filename)[0]
        return f"{base_name}_summary.txt"
            
    def batch_summarize(self, text_files: List[str]) -> Dict[str, List[str]]:
        """Generates summaries for multiple text files"""
        results = {
            'success': [],
            'failed': []
        }
        
        for text_path in text_files:
            if not os.path.exists(text_path):
                self.logger.error(f"Text file not found: {text_path}")
                results['failed'].append(text_path)
                continue
                
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read()
                
            filename = os.path.basename(text_path)
            output_path = self.generate_summary(text, filename)
            
            if output_path:
                results['success'].append(output_path)
            else:
                results['failed'].append(text_path)
                
        self.logger.info(f"Summary generation complete. Success: {len(results['success'])}, Failed: {len(results['failed'])}")
        return results 