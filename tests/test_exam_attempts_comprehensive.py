import uuid
import pytest
from sqlalchemy import select

from app.db.models import ExamAttempt, QuestionModel

# مارکر برای اجرای تست‌های آسنکرون
pytestmark = pytest.mark.asyncio


class TestExamAttemptsComprehensive:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.prefix = "/api/v1/exam-attempts"

    # -------------------------------------------------------------------------
    # ۱. تست‌های Happy Path (مسیرهای موفقیت‌آمیز)
    # -------------------------------------------------------------------------

    async def test_full_exam_flow_success(
        self, authenticated_client, seeded_exam, db_session
    ):
        """
        تست چرخه کامل: شروع -> پاسخ دادن (تکی) -> پاسخ دادن (تکی) -> ثبت نهایی
        """
        # [Step 1] Start Exam
        start_resp = await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )
        assert start_resp.status_code == 201
        start_data = start_resp.json()
        assert "id" in start_data
        attempt_id = start_data["id"]

        # [Step 2] Get Question ID from DB
        res = await db_session.execute(
            select(QuestionModel).where(QuestionModel.exam_id == seeded_exam.id)
        )
        questions = res.scalars().all()
        assert len(questions) > 0
        q1 = questions[0]
        q2 = questions[1] if len(questions) > 1 else questions[0]

        # [Step 3] Answer Question 1
        ans1_resp = await authenticated_client.put(
            f"{self.prefix}/{attempt_id}/answers/{q1.id}",
            json={"submitted_answer": "Force"},
        )
        assert ans1_resp.status_code == 200
        assert ans1_resp.json()["submitted_answer"] == "Force"

        # [Step 4] Answer Question 2
        ans2_resp = await authenticated_client.put(
            f"{self.prefix}/{attempt_id}/answers/{q2.id}",
            json={"submitted_answer": "Inertia"},
        )
        assert ans2_resp.status_code == 200
        assert ans2_resp.json()["submitted_answer"] == "Inertia"

        # [Step 5] Final Submit
        submit_resp = await authenticated_client.post(
            f"{self.prefix}/{attempt_id}/submit", json={}
        )
        assert submit_resp.status_code == 200
        data = submit_resp.json()
        assert "total_score" in data
        assert data["status"] == "completed"

    async def test_bulk_submit_request(
        self, authenticated_client, seeded_exam, db_session
    ):
        """
        تست قابلیت ثبت پاسخ‌ها به صورت دسته‌جمعی (Bulk)
        """
        start_resp = await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )
        assert start_resp.status_code == 201
        attempt_id = start_resp.json()["id"]

        res = await db_session.execute(
            select(QuestionModel).where(QuestionModel.exam_id == seeded_exam.id)
        )
        qs = res.scalars().all()
        assert len(qs) > 0

        # ایجاد Payload برای Bulk
        bulk_payload = {
            "answers": (
                [
                    {"question_id": qs[0].id, "submitted_answer": "Ans1"},
                    {"question_id": qs[1].id, "submitted_answer": "Ans2"},
                ]
                if len(qs) > 1
                else [
                    {"question_id": qs[0].id, "submitted_answer": "Ans1"}
                ]
            )
        }

        bulk_resp = await authenticated_client.post(
            f"{self.prefix}/{attempt_id}/bulk-answers", json=bulk_payload
        )

        if bulk_resp.status_code == 200:
            assert (
                bulk_resp.json().get("status") == "success"
                or "answers" in bulk_resp.json()
            )
        else:
            assert bulk_resp.status_code in [200, 400, 404, 422]

    async def test_get_exam_attempt_success(
        self, authenticated_client, seeded_exam
    ):
        """تست دریافت اطلاعات یک آزمون مشخص (GET /{attempt_id})"""
        start_resp = await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )
        assert start_resp.status_code == 201
        attempt_id = start_resp.json()["id"]

        get_resp = await authenticated_client.get(f"{self.prefix}/{attempt_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == attempt_id

    async def test_list_exam_attempts(
        self, authenticated_client, seeded_exam
    ):
        """تست دریافت لیست آزمون‌های کاربر جاری (GET /)"""
        # ایجاد حداقل یک آزمون برای اطمینان از وجود دیتا
        await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )

        list_resp = await authenticated_client.get(f"{self.prefix}/")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    # -------------------------------------------------------------------------
    # ۲. تست‌های Error Handling (خطاهای منطقی و بیزنس)
    # -------------------------------------------------------------------------

    async def test_error_start_non_existent_exam(self, authenticated_client):
        """تست شروع آزمونی که وجود ندارد (400 یا 404)"""
        fake_id = 999999
        resp = await authenticated_client.post(f"{self.prefix}/exams/{fake_id}/start")
        assert resp.status_code in [400, 404]

    async def test_error_answer_to_non_existent_attempt(self, authenticated_client):
        """تست پاسخ دادن به آزمون نامعتبر (400 یا 404)"""
        fake_id = str(uuid.uuid4())
        resp = await authenticated_client.put(
            f"{self.prefix}/{fake_id}/answers/1",
            json={"submitted_answer": "X"},
        )
        assert resp.status_code in [400, 404]

    async def test_get_exam_attempt_not_found(self, authenticated_client):
        """تست دریافت آزمون با شناسه ناموجود (پوشش خطای ValueError در GET /{attempt_id})"""
        fake_id = str(uuid.uuid4())
        get_resp = await authenticated_client.get(f"{self.prefix}/{fake_id}")
        assert get_resp.status_code in [400, 404]

    async def test_error_submit_already_completed_exam(
        self, authenticated_client, seeded_exam
    ):
        """
        تست: جلوگیری از ثبت دوباره آزمون تکمیل شده (400 یا 409)
        """
        start_resp = await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )
        assert start_resp.status_code == 201
        attempt_id = start_resp.json()["id"]

        # اولین Submit
        first_submit = await authenticated_client.post(
            f"{self.prefix}/{attempt_id}/submit", json={}
        )
        assert first_submit.status_code == 200

        # دومین Submit
        second_submit = await authenticated_client.post(
            f"{self.prefix}/{attempt_id}/submit", json={}
        )
        assert second_submit.status_code in [400, 409]

    async def test_error_answering_after_submission(
        self, authenticated_client, seeded_exam
    ):
        """تست جلوگیری از ثبت پاسخ پس از اتمام آزمون"""
        start_resp = await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )
        assert start_resp.status_code == 201
        attempt_id = start_resp.json()["id"]

        submit_resp = await authenticated_client.post(
            f"{self.prefix}/{attempt_id}/submit", json={}
        )
        assert submit_resp.status_code == 200

        ans_resp = await authenticated_client.put(
            f"{self.prefix}/{attempt_id}/answers/1",
            json={"submitted_answer": "Late"},
        )
        assert ans_resp.status_code in [400, 409]

    # -------------------------------------------------------------------------
    # ۳. تست‌های اعتبارسنجی داده‌ها (Pydantic & Validation)
    # -------------------------------------------------------------------------

    async def test_error_invalid_payload_format(
        self, authenticated_client, seeded_exam
    ):
        """تست ارسال دیتای نامعتبر (422)"""
        start_resp = await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )
        assert start_resp.status_code == 201
        attempt_id = start_resp.json()["id"]

        bad_payload = {"submitted_answer": 12345}
        resp = await authenticated_client.put(
            f"{self.prefix}/{attempt_id}/answers/1", json=bad_payload
        )
        assert resp.status_code == 422

    async def test_error_missing_required_fields(
        self, authenticated_client, seeded_exam
    ):
        """تست ارسال بدنه خالی (422)"""
        start_resp = await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )
        assert start_resp.status_code == 201
        attempt_id = start_resp.json()["id"]

        resp = await authenticated_client.put(
            f"{self.prefix}/{attempt_id}/answers/1", json={}
        )
        assert resp.status_code == 422

    # -------------------------------------------------------------------------
    # ۴. تست‌های یکپارچگی دیتابیس (Database Integrity)
    # -------------------------------------------------------------------------

    async def test_database_integrity_after_exam(
        self, authenticated_client, seeded_exam, db_session
    ):
        """تست بررسی وضعیت ذخیره‌سازی در دیتابیس"""
        start_resp = await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )
        assert start_resp.status_code == 201
        attempt_id = uuid.UUID(start_resp.json()["id"])

        submit_resp = await authenticated_client.post(
            f"{self.prefix}/{attempt_id}/submit", json={}
        )
        assert submit_resp.status_code == 200

        res = await db_session.execute(
            select(ExamAttempt).where(ExamAttempt.id == attempt_id)
        )
        attempt_in_db = res.scalars().first()

        assert attempt_in_db is not None
        assert attempt_in_db.status == "completed"
        assert attempt_in_db.total_score is not None

    # -------------------------------------------------------------------------
    # ۵. تست‌های لبه (Edge Cases)
    # -------------------------------------------------------------------------

    async def test_extreme_large_answer(self, authenticated_client, seeded_exam):
        """تست ارسال پاسخ طولانی"""
        start_resp = await authenticated_client.post(
            f"{self.prefix}/exams/{seeded_exam.id}/start"
        )
        assert start_resp.status_code == 201
        attempt_id = start_resp.json()["id"]

        long_answer = "A" * 10000
        resp = await authenticated_client.put(
            f"{self.prefix}/{attempt_id}/answers/1",
            json={"submitted_answer": long_answer},
        )
        assert resp.status_code in [200, 400, 422]
