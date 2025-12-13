from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph
import os

def create_test_pdf(filename="test_document.pdf", num_pages=2):
    """Create a test PDF with sample text content"""
    
    # Sample text that will be chunked and embedded
    sample_texts = [
        """This is a sample PDF document for testing the upload endpoint. 
        The system will extract text from this PDF, chunk it into smaller segments,
        and create embeddings using sentence transformers. This is the first paragraph
        with some content that demonstrates text extraction capabilities.""",
        
        """Here is the second paragraph with different content. The chunking process
        will break this text into segments of approximately 800 characters with 100
        character overlap between chunks. This allows for better semantic search
        and retrieval of relevant information from the document.""",
        
        """The third paragraph contains more sample text to ensure we have enough
        content for multiple chunks. Machine learning models like sentence transformers
        work better with larger amounts of text, so having multiple paragraphs helps
        test the embedding quality and chunking logic.""",
        
        """Finally, this fourth paragraph provides additional content for testing.
        The PDF processing pipeline includes text extraction using PyMuPDF, text
        chunking with configurable overlap, and embedding generation using the
        all-MiniLM-L6-v2 model by default."""
    ]
    
    # Create PDF
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    for i, text in enumerate(sample_texts * num_pages):
        story.append(Paragraph(f"<b>Paragraph {i+1}:</b> {text}", styles["Normal"]))
        story.append(Paragraph("<br/><br/>", styles["Normal"]))
    
    doc.build(story)
    print(f"Test PDF created: {filename}")

if __name__ == "__main__":
    create_test_pdf("test_document.pdf")