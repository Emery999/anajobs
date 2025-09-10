#!/usr/bin/env python3
"""
Demo AI Job Title Extraction

Shows how the AI extraction would work with sample content
"""

def demo_extraction():
    """Demo the AI extraction process with sample content"""
    print("🎬 Demo: AI Job Title Extraction Process")
    print("=" * 50)
    
    # Sample aggregated job content (like what would be collected)
    sample_content = """
=== ROOT JOBS PAGE: https://sample-org.org/careers ===
Careers at SampleOrg
Join our mission to create positive change

Current Openings:

Software Engineer - Climate Tech
We're looking for a passionate software engineer to build tools for climate action.

Senior Data Scientist 
Help us analyze environmental data to drive policy decisions.

Program Manager, Renewable Energy
Lead our renewable energy initiatives across multiple projects.

Marketing Coordinator
Support our communications and outreach efforts.

Apply Now | Learn More | View Benefits

=== JOB PAGE: https://sample-org.org/careers/engineering ===
Engineering Opportunities

Frontend Developer
Build user interfaces for our web applications.

Backend Engineer
Develop APIs and server-side systems.

DevOps Specialist
Manage our cloud infrastructure and deployment pipelines.

=== JOB PAGE: https://sample-org.org/careers/programs ===
Program Team

Director of Programs
Oversee all program activities and strategic planning.

Field Coordinator
Coordinate on-ground activities in project locations.
"""
    
    print("📚 Sample Aggregated Content:")
    print("-" * 40)
    print(sample_content[:500] + "...")
    print(f"\nTotal content length: {len(sample_content)} characters")
    
    print("\n🤖 AI Extraction Process:")
    print("1. Send content to Claude AI with specialized prompt")
    print("2. Claude identifies actual job titles vs. other text")
    print("3. Returns clean JSON array of exact titles")
    
    print("\n✅ Expected AI-Extracted Job Titles:")
    expected_titles = [
        "Software Engineer - Climate Tech",
        "Senior Data Scientist", 
        "Program Manager, Renewable Energy",
        "Marketing Coordinator",
        "Frontend Developer",
        "Backend Engineer", 
        "DevOps Specialist",
        "Director of Programs",
        "Field Coordinator"
    ]
    
    for i, title in enumerate(expected_titles, 1):
        print(f"   {i}. {title}")
    
    print(f"\n📊 Results: {len(expected_titles)} precise job titles extracted")
    print("🎯 AI filters out: 'Apply Now', 'Learn More', 'View Benefits', etc.")
    
    print("\n💾 Database Update:")
    print("   job_titles: [\"Software Engineer - Climate Tech\", \"Senior Data Scientist\", ...]")
    print("   job_titles_extraction_method: \"claude_ai\"")
    print("   job_titles_updated_at: \"2025-09-09T19:15:00\"")
    
    return 0

if __name__ == "__main__":
    demo_extraction()