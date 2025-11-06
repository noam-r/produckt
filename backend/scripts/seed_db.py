"""
Database seeding script for development.
Creates sample organizations, users, and test data.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import SessionLocal, engine, Base
from backend.models import (
    Organization, User, UserRole, Context, Initiative, InitiativeStatus,
    Question, QuestionCategory, QuestionPriority, Answer, AnswerStatus
)
from backend.auth.password import hash_password


def seed_database():
    """Seed the database with sample data."""

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        print("Seeding database...")

        # Check if data already exists
        if db.query(Organization).first():
            print("Database already contains data. Skipping seed.")
            return

        # Create organizations
        print("Creating organizations...")
        acme = Organization(name="Acme Corp")
        tech_start = Organization(name="TechStart Inc")
        db.add_all([acme, tech_start])
        db.flush()

        # Create users
        print("Creating users...")
        users = [
            User(
                email="admin@acme.com",
                password_hash=hash_password("Admin123!"),
                name="Admin User",
                role=UserRole.ADMIN,
                organization_id=acme.id,
                is_active=True
            ),
            User(
                email="pm@acme.com",
                password_hash=hash_password("ProductMgr123!"),
                name="Alice Product Manager",
                role=UserRole.PRODUCT_MANAGER,
                organization_id=acme.id,
                is_active=True
            ),
            User(
                email="contributor@acme.com",
                password_hash=hash_password("Contributor123!"),
                name="Bob Contributor",
                role=UserRole.CONTRIBUTOR,
                organization_id=acme.id,
                is_active=True
            ),
            User(
                email="viewer@acme.com",
                password_hash=hash_password("Viewer123!"),
                name="Charlie Viewer",
                role=UserRole.VIEWER,
                organization_id=acme.id,
                is_active=True
            ),
            User(
                email="pm@techstart.com",
                password_hash=hash_password("TechPM123!"),
                name="Dana Tech PM",
                role=UserRole.PRODUCT_MANAGER,
                organization_id=tech_start.id,
                is_active=True
            ),
        ]
        db.add_all(users)
        db.flush()

        # Get users for references
        alice = users[1]  # PM at Acme
        dana = users[4]   # PM at TechStart

        # Create context for Acme
        print("Creating organizational context...")
        acme_context = Context(
            organization_id=acme.id,
            company_mission="To provide innovative enterprise solutions that transform business operations",
            strategic_objectives="1. Increase market share by 25%\n2. Launch 3 new products\n3. Expand to EMEA region",
            target_markets="Mid-market to enterprise B2B SaaS customers",
            competitive_landscape="Competing with Salesforce, ServiceNow, and emerging AI-first startups",
            technical_constraints="Tech Stack: Python, React, PostgreSQL, AWS\nBudget: $2M, Timeline: 6 months, Team: 15 engineers",
            version=1,
            is_current=True,
            created_by=alice.id
        )
        db.add(acme_context)
        db.flush()

        # Create initiatives
        print("Creating initiatives...")
        ai_sales_tool = Initiative(
            title="AI-Powered Sales Assistant",
            description="An intelligent sales assistant that uses Claude to help sales reps qualify leads, draft emails, and suggest next best actions based on CRM data and conversation history.",
            status=InitiativeStatus.IN_QA,
            organization_id=acme.id,
            created_by=alice.id,
            iteration_count=2,
            readiness_score=75.5
        )

        customer_analytics = Initiative(
            title="Customer Analytics Dashboard",
            description="Real-time analytics dashboard showing customer health scores, usage patterns, and churn risk indicators.",
            status=InitiativeStatus.DRAFT,
            organization_id=acme.id,
            created_by=alice.id,
            iteration_count=0
        )

        mobile_app = Initiative(
            title="Mobile App Redesign",
            description="Complete redesign of our mobile application with focus on offline-first capabilities and improved UX.",
            status=InitiativeStatus.READY,
            organization_id=acme.id,
            created_by=alice.id,
            iteration_count=3,
            readiness_score=92.0
        )

        db.add_all([ai_sales_tool, customer_analytics, mobile_app])
        db.flush()

        # Create questions for AI Sales Tool
        print("Creating questions and answers...")
        questions_data = [
            {
                "initiative": ai_sales_tool,
                "iteration": 1,
                "category": QuestionCategory.BUSINESS_DEV,
                "priority": QuestionPriority.P0,
                "blocks_mrd": True,
                "question": "What is the Total Addressable Market (TAM) for AI-powered sales tools?",
                "rationale": "Need to understand market size to justify investment and set growth targets",
                "answer": "$15B globally, growing at 35% CAGR. Our target segment (mid-market B2B) represents $4B.",
                "status": AnswerStatus.ANSWERED
            },
            {
                "initiative": ai_sales_tool,
                "iteration": 1,
                "category": QuestionCategory.TECHNICAL,
                "priority": QuestionPriority.P0,
                "blocks_mrd": True,
                "question": "What are the technical requirements for integrating with existing CRM systems?",
                "rationale": "Integration complexity will impact development timeline and resource needs",
                "answer": "REST APIs available for Salesforce, HubSpot, Pipedrive. OAuth2 authentication required. Estimated 4-6 weeks for integration work.",
                "status": AnswerStatus.ANSWERED
            },
            {
                "initiative": ai_sales_tool,
                "iteration": 2,
                "category": QuestionCategory.PRODUCT,
                "priority": QuestionPriority.P1,
                "blocks_mrd": False,
                "question": "What specific workflows should the AI assistant support in v1?",
                "rationale": "Need to define MVP scope to ensure focused development",
                "answer": "V1 will support: 1) Lead qualification scoring, 2) Email draft generation, 3) Meeting summary and next steps",
                "status": AnswerStatus.ANSWERED
            },
            {
                "initiative": ai_sales_tool,
                "iteration": 2,
                "category": QuestionCategory.FINANCIAL,
                "priority": QuestionPriority.P1,
                "blocks_mrd": False,
                "question": "What is the expected ROI and payback period?",
                "rationale": "Finance team needs ROI analysis for budget approval",
                "answer": None,
                "status": AnswerStatus.UNKNOWN
            },
            {
                "initiative": customer_analytics,
                "iteration": 1,
                "category": QuestionCategory.TECHNICAL,
                "priority": QuestionPriority.P0,
                "blocks_mrd": True,
                "question": "What data sources need to be integrated for comprehensive customer analytics?",
                "rationale": "Must identify all required data sources to architect the solution properly",
                "answer": None,
                "status": AnswerStatus.UNKNOWN
            },
        ]

        for q_data in questions_data:
            question = Question(
                initiative_id=q_data["initiative"].id,
                iteration=q_data["iteration"],
                category=q_data["category"],
                priority=q_data["priority"],
                blocks_mrd_generation=q_data["blocks_mrd"],
                question_text=q_data["question"],
                rationale=q_data["rationale"]
            )
            db.add(question)
            db.flush()

            if q_data["answer"]:
                answer = Answer(
                    question_id=question.id,
                    answer_text=q_data["answer"],
                    answer_status=q_data["status"],
                    answered_by=alice.id
                )
                db.add(answer)

        # Commit all changes
        db.commit()

        print("\n" + "="*60)
        print("Database seeded successfully!")
        print("="*60)
        print("\nSample Users:")
        print("-" * 60)
        print(f"Admin:        admin@acme.com        / Admin123!")
        print(f"PM:           pm@acme.com           / ProductMgr123!")
        print(f"Contributor:  contributor@acme.com  / Contributor123!")
        print(f"Viewer:       viewer@acme.com       / Viewer123!")
        print(f"TechStart PM: pm@techstart.com      / TechPM123!")
        print("-" * 60)
        print(f"\nOrganizations: {db.query(Organization).count()}")
        print(f"Users: {db.query(User).count()}")
        print(f"Initiatives: {db.query(Initiative).count()}")
        print(f"Questions: {db.query(Question).count()}")
        print(f"Answers: {db.query(Answer).count()}")
        print("\nYou can now login with any of the above credentials!")
        print("="*60)

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
