"""
Property-based tests for QuestionThrottleService.
"""

import pytest
from uuid import uuid4

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from sqlalchemy.orm import Session

from backend.services.question_throttle_service import QuestionThrottleService
from backend.models.question import Question, QuestionCategory, QuestionPriority
from backend.models.answer import Answer, AnswerStatus
from backend.models.initiative import Initiative, InitiativeStatus
from backend.models.organization import Organization
from backend.models.user import User, UserRoleEnum


class TestQuestionThrottleServiceProperties:
    """Property-based tests for QuestionThrottleService."""

    @pytest.fixture
    def throttle_service(self, test_db: Session):
        """Create a QuestionThrottleService instance."""
        return QuestionThrottleService(test_db)

    @pytest.fixture
    def test_initiative_with_limit(self, test_db: Session, test_organization: Organization, test_user: User):
        """Create a test initiative with a specific question limit."""
        def _create_initiative(max_questions: int = 50):
            initiative = Initiative(
                title=f"Test Initiative {uuid4()}",
                description="Test initiative description",
                status=InitiativeStatus.DRAFT,
                organization_id=test_organization.id,
                created_by=test_user.id,
                iteration_count=0,
                max_questions=max_questions
            )
            test_db.add(initiative)
            test_db.commit()
            test_db.refresh(initiative)
            return initiative
        return _create_initiative

    def _create_question(self, test_db: Session, initiative_id, iteration: int = 1):
        """Helper to create a question."""
        question = Question(
            initiative_id=initiative_id,
            iteration=iteration,
            category=QuestionCategory.BUSINESS_DEV,
            priority=QuestionPriority.P1,
            question_text=f"Test question {uuid4()}",
            rationale="Test rationale"
        )
        test_db.add(question)
        test_db.commit()
        test_db.refresh(question)
        return question

    def _create_answer(self, test_db: Session, question_id, status: AnswerStatus, user_id):
        """Helper to create an answer."""
        answer = Answer(
            question_id=question_id,
            answer_status=status,
            answer_text="Test answer" if status == AnswerStatus.ANSWERED else None,
            answered_by=user_id
        )
        test_db.add(answer)
        test_db.commit()
        test_db.refresh(answer)
        return answer

    @given(
        unanswered_count=st.integers(min_value=0, max_value=10),
        answered_count=st.integers(min_value=0, max_value=10),
        max_questions=st.integers(min_value=10, max_value=100)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=2000)
    def test_question_generation_throttling(
        self,
        throttle_service: QuestionThrottleService,
        test_initiative_with_limit,
        test_db: Session,
        test_user: User,
        unanswered_count: int,
        answered_count: int,
        max_questions: int
    ):
        """
        **Feature: cost-controls, Property 3: Question Generation Throttling**
        **Validates: Requirements 3.2, 3.3**
        
        For any initiative with 5 or more unanswered questions, attempting to 
        generate additional questions should be rejected.
        """
        # Ensure we don't exceed the max questions limit in our test setup
        total_questions = unanswered_count + answered_count
        assume(total_questions <= max_questions)
        
        # Create initiative with specified limit
        initiative = test_initiative_with_limit(max_questions)
        
        # Create unanswered questions (no answers)
        for _ in range(unanswered_count):
            self._create_question(test_db, initiative.id)
        
        # Create answered questions
        for _ in range(answered_count):
            question = self._create_question(test_db, initiative.id)
            self._create_answer(test_db, question.id, AnswerStatus.ANSWERED, test_user.id)
        
        # Check if questions can be generated
        result = throttle_service.can_generate_questions(initiative.id)
        
        # Property: If 5 or more unanswered questions exist, generation should be blocked
        if unanswered_count >= 5:
            assert not result.can_generate, f"Should block generation with {unanswered_count} unanswered questions"
            assert "unanswered questions" in result.reason.lower()
        elif total_questions >= max_questions:
            # Also blocked if at max questions limit
            assert not result.can_generate, f"Should block generation at max limit ({total_questions}/{max_questions})"
            assert "maximum question limit" in result.reason.lower()
        else:
            assert result.can_generate, f"Should allow generation with {unanswered_count} unanswered questions and {total_questions}/{max_questions} total"
        
        # Verify counts are correct
        assert result.unanswered_count == unanswered_count
        assert result.total_count == total_questions
        assert result.max_questions == max_questions

    @given(
        questions_without_answers=st.integers(min_value=0, max_value=10),
        questions_with_unknown=st.integers(min_value=0, max_value=5),
        questions_with_skipped=st.integers(min_value=0, max_value=5),
        questions_with_estimated=st.integers(min_value=0, max_value=5),
        questions_answered=st.integers(min_value=0, max_value=10)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=2000)
    def test_unanswered_question_count_accuracy(
        self,
        throttle_service: QuestionThrottleService,
        test_initiative_with_limit,
        test_db: Session,
        test_user: User,
        questions_without_answers: int,
        questions_with_unknown: int,
        questions_with_skipped: int,
        questions_with_estimated: int,
        questions_answered: int
    ):
        """
        **Feature: cost-controls, Property 5: Unanswered Question Count Accuracy**
        **Validates: Requirements 3.4, 3.5**
        
        For any initiative, the count of unanswered questions should equal the number 
        of questions with status "Pending", "In Progress", or "Unknown".
        """
        total_questions = (questions_without_answers + questions_with_unknown + 
                          questions_with_skipped + questions_with_estimated + questions_answered)
        
        # Ensure we don't exceed reasonable limits
        assume(total_questions <= 50)
        
        # Create initiative
        initiative = test_initiative_with_limit(100)  # High limit to avoid interference
        
        # Create questions without answers
        for _ in range(questions_without_answers):
            self._create_question(test_db, initiative.id)
        
        # Create questions with "Unknown" status
        for _ in range(questions_with_unknown):
            question = self._create_question(test_db, initiative.id)
            self._create_answer(test_db, question.id, AnswerStatus.UNKNOWN, test_user.id)
        
        # Create questions with "Skipped" status
        for _ in range(questions_with_skipped):
            question = self._create_question(test_db, initiative.id)
            self._create_answer(test_db, question.id, AnswerStatus.SKIPPED, test_user.id)
        
        # Create questions with "Estimated" status
        for _ in range(questions_with_estimated):
            question = self._create_question(test_db, initiative.id)
            self._create_answer(test_db, question.id, AnswerStatus.ESTIMATED, test_user.id)
        
        # Create answered questions
        for _ in range(questions_answered):
            question = self._create_question(test_db, initiative.id)
            self._create_answer(test_db, question.id, AnswerStatus.ANSWERED, test_user.id)
        
        # Count unanswered questions
        unanswered_count = throttle_service.count_unanswered_questions(initiative.id)
        
        # Property: Unanswered count should equal questions without answers + questions with unanswered statuses
        expected_unanswered = (questions_without_answers + questions_with_unknown + 
                              questions_with_skipped + questions_with_estimated)
        
        assert unanswered_count == expected_unanswered, (
            f"Expected {expected_unanswered} unanswered questions, got {unanswered_count}. "
            f"Breakdown: {questions_without_answers} without answers, {questions_with_unknown} unknown, "
            f"{questions_with_skipped} skipped, {questions_with_estimated} estimated, {questions_answered} answered"
        )

    @given(
        current_questions=st.integers(min_value=0, max_value=20),
        max_questions=st.integers(min_value=5, max_value=50),
        questions_to_add=st.integers(min_value=1, max_value=10)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=2000)
    def test_initiative_question_limit_enforcement(
        self,
        throttle_service: QuestionThrottleService,
        test_initiative_with_limit,
        test_db: Session,
        test_user: User,
        current_questions: int,
        max_questions: int,
        questions_to_add: int
    ):
        """
        **Feature: cost-controls, Property 8: Initiative Question Limit Enforcement**
        **Validates: Requirements 5.3**
        
        For any initiative at its maximum question limit, attempting to generate 
        additional questions should be rejected.
        """
        # Ensure current questions don't exceed max
        assume(current_questions <= max_questions)
        
        # Create initiative with specified limit
        initiative = test_initiative_with_limit(max_questions)
        
        # Create current questions (mix of answered and unanswered, but keep unanswered < 5 to avoid throttling)
        unanswered_created = 0
        for i in range(current_questions):
            question = self._create_question(test_db, initiative.id)
            # Answer some questions to avoid unanswered throttling
            if unanswered_created >= 4:  # Keep unanswered count below 5
                self._create_answer(test_db, question.id, AnswerStatus.ANSWERED, test_user.id)
            else:
                unanswered_created += 1
        
        # Check if we can add more questions
        result = throttle_service.check_question_limits(initiative.id, questions_to_add)
        
        # Property: If adding questions would exceed max limit, it should be rejected
        would_exceed_limit = (current_questions + questions_to_add) > max_questions
        
        if would_exceed_limit:
            assert not result.can_add, (
                f"Should reject adding {questions_to_add} questions when current={current_questions}, max={max_questions}"
            )
            assert "maximum limit" in result.reason.lower()
        elif unanswered_created >= 5:
            # Also blocked by unanswered throttling
            assert not result.can_add, f"Should be blocked by unanswered throttling ({unanswered_created} unanswered)"
        else:
            assert result.can_add, (
                f"Should allow adding {questions_to_add} questions when current={current_questions}, max={max_questions}"
            )
        
        # Verify counts are correct
        assert result.total_count == current_questions
        assert result.max_questions == max_questions
        assert result.questions_to_add == questions_to_add

    @given(
        total_questions=st.integers(min_value=0, max_value=30),
        answered_ratio=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=2000)
    def test_total_question_count_accuracy(
        self,
        throttle_service: QuestionThrottleService,
        test_initiative_with_limit,
        test_db: Session,
        test_user: User,
        total_questions: int,
        answered_ratio: float
    ):
        """
        **Feature: cost-controls, Property 10: Total Question Count Accuracy**
        **Validates: Requirements 5.4**
        
        For any initiative, the total question count should equal the number of all 
        questions (answered and unanswered) associated with that initiative.
        """
        # Create initiative
        initiative = test_initiative_with_limit(100)  # High limit to avoid interference
        
        # Calculate how many questions to answer
        answered_count = int(total_questions * answered_ratio)
        unanswered_count = total_questions - answered_count
        
        # Create questions
        questions = []
        for _ in range(total_questions):
            question = self._create_question(test_db, initiative.id)
            questions.append(question)
        
        # Answer some questions
        for i in range(answered_count):
            self._create_answer(test_db, questions[i].id, AnswerStatus.ANSWERED, test_user.id)
        
        # Count total questions
        actual_count = throttle_service.count_total_questions(initiative.id)
        
        # Property: Total count should equal all questions regardless of answer status
        assert actual_count == total_questions, (
            f"Expected {total_questions} total questions, got {actual_count}. "
            f"({answered_count} answered, {unanswered_count} unanswered)"
        )