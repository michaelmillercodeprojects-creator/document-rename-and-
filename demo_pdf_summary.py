#!/usr/bin/env python3
"""
Demo script showing the new PDF summary functionality
"""

import os
import sys
from pathlib import Path

def create_demo_documents():
    """Create some demo documents for testing"""
    demo_dir = Path("demo_docs")
    demo_dir.mkdir(exist_ok=True)
    
    # Create various types of demo documents
    documents = [
        ("quarterly_report_2024-Q3.txt", """Quarterly Financial Report - Q3 2024

Executive Summary:
This report presents the financial performance for the third quarter of 2024.
Revenue increased by 18% compared to Q2 2024, reaching $2.3M.
Operating expenses were controlled at $1.8M, showing improved efficiency.

Key Highlights:
- Customer acquisition increased by 25%
- Product line A showed 30% growth
- International sales expanded to 3 new markets

Recommendations:
Continue investment in high-growth product lines and expand marketing efforts."""),

        ("meeting_notes_sept_15_2024.md", """# Board Meeting Notes
Date: September 15, 2024
Attendees: CEO, CFO, COO, Board Members

## Agenda Items Discussed:

### 1. Financial Performance Review
- Q3 results exceed expectations
- Cash flow remains strong
- Investment opportunities identified

### 2. Strategic Planning
- Market expansion strategy approved
- Technology infrastructure upgrade planned
- New hiring initiatives authorized

### Action Items:
- [ ] Prepare detailed expansion proposal (Due: Oct 1)
- [ ] Review infrastructure vendors (Due: Oct 15)
- [ ] Submit budget proposals (Due: Nov 1)"""),

        ("contract_amendment_2024.txt", """CONTRACT AMENDMENT - Service Agreement

Amendment Date: August 22, 2024
Original Contract Date: January 10, 2024
Parties: TechCorp Inc. and ServiceProvider LLC

This amendment modifies the following terms:
1. Service delivery timeline extended to December 31, 2024
2. Additional services added: data migration and training
3. Payment terms adjusted to net-30 days
4. Milestone deliverables updated per attached schedule

Both parties agree to these modifications effective immediately.
Signatures required by both parties within 15 business days."""),

        ("invoice_2024_001.txt", """INVOICE #2024-001

Bill To: ABC Corporation
Invoice Date: July 15, 2024
Due Date: August 15, 2024

Services Rendered:
- Consulting Services (40 hours @ $150/hr): $6,000
- Project Management (20 hours @ $125/hr): $2,500
- Documentation (10 hours @ $100/hr): $1,000

Subtotal: $9,500
Tax (8.5%): $807.50
Total Amount Due: $10,307.50

Payment Terms: Net 30 days
Thank you for your business!"""),

        ("research_paper_draft.txt", """Research Paper: Digital Transformation in Small Business

Abstract:
This study examines the impact of digital transformation initiatives on small business performance.
Through analysis of 200 companies over 18 months, we identify key success factors and common challenges.

Introduction:
Digital transformation has become critical for business survival in the modern economy.
Small businesses face unique challenges in implementing these changes due to resource constraints.

Methodology:
- Survey of 200 small businesses (50-250 employees)
- 18-month longitudinal study
- Performance metrics tracked quarterly
- Qualitative interviews with leadership teams

Findings:
Companies that invested in digital transformation showed 23% average revenue growth.
Key success factors include leadership commitment and employee training.
Main barriers include budget constraints and technical expertise gaps.""")
    ]
    
    for filename, content in documents:
        file_path = demo_dir / filename
        file_path.write_text(content)
    
    return demo_dir

def run_demonstrations():
    """Run various demonstrations of the tool"""
    print("🎯 Document Renamer - PDF Summary Feature Demo")
    print("=" * 60)
    
    # Create demo documents
    print("\n1. Creating demo documents...")
    demo_dir = create_demo_documents()
    print(f"✅ Created {len(list(demo_dir.glob('*')))} demo documents in '{demo_dir}'")
    
    # Show original files
    print(f"\n📁 Original files in {demo_dir}:")
    for file_path in sorted(demo_dir.glob("*.txt")) + sorted(demo_dir.glob("*.md")):
        size = file_path.stat().st_size
        print(f"   📄 {file_path.name} ({size} bytes)")
    
    print("\n" + "=" * 60)
    
    # Demo 1: Create PDF summary without renaming
    print("\n2. 📋 Creating PDF Summary (without renaming files)...")
    print("   Command: python document_renamer.py demo_docs --summarize-only")
    print("-" * 40)
    
    os.system(f"python document_renamer.py {demo_dir} --summarize-only")
    
    # Show what was created
    pdf_files = list(demo_dir.glob("*.pdf"))
    if pdf_files:
        pdf_file = pdf_files[0]
        print(f"\n✅ PDF Summary created: {pdf_file.name}")
        print(f"   📍 Location: {pdf_file.resolve()}")
        print(f"   📊 Size: {pdf_file.stat().st_size:,} bytes")
    
    print("\n" + "=" * 60)
    
    # Demo 2: Show normal renaming functionality  
    print("\n3. 📝 Normal Renaming Operation (dry run)...")
    print("   Command: python document_renamer.py demo_docs --dry-run")
    print("-" * 40)
    
    os.system(f"python document_renamer.py {demo_dir} --dry-run")
    
    print("\n" + "=" * 60)
    
    # Demo 3: Show help
    print("\n4. 📚 Available Options:")
    print("   Command: python document_renamer.py --help")
    print("-" * 40)
    
    os.system("python document_renamer.py --help")
    
    print("\n" + "=" * 60)
    
    # Summary
    print("\n🎉 Demo Complete! Key Features Demonstrated:")
    print("   ✅ PDF Summary Generation (--summarize-only)")
    print("   ✅ Document Analysis without File Changes")
    print("   ✅ Professional PDF Output with Summaries")
    print("   ✅ Compatible with ChatGPT API Integration")
    print("   ✅ Normal File Renaming Functionality")
    
    print(f"\n📂 Demo files remain in: {demo_dir.resolve()}")
    print("💡 To test with ChatGPT API:")
    print("   python document_renamer.py demo_docs --summarize-only --openai-api-key 'your-key'")
    
    print("\n🚀 Ready for production use!")

if __name__ == "__main__":
    run_demonstrations()