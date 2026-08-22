import unittest

from app.services.exams.question_service import generate_questions


class TestQuestionService(unittest.TestCase):
    def test_generate_questions_returns_correct_count(self):
        # بررسی اینکه تعداد سوالات تولید شده با عدد درخواستی برابر باشد
        topic = "فیزیک"
        grade = 10
        count = 5

        questions = generate_questions(topic, grade, count)

        self.assertEqual(len(questions), count)

    def test_generate_questions_structure(self):
        # بررسی ساختار هر سوال تولید شده
        topic = "ریاضی"
        grade = 12
        count = 1

        questions = generate_questions(topic, grade, count)
        q = questions[0]

        # بررسی وجود کلیدهای اصلی
        self.assertIn("question", q)
        self.assertIn("options", q)
        self.assertIn("answer", q)

        # بررسی محتوای فیلدها
        self.assertTrue(q["question"].startswith("سوال"))
        self.assertIn(topic, q["question"])
        self.assertIn(str(grade), q["question"])
        self.assertEqual(len(q["options"]), 4)
        self.assertTrue(1 <= q["answer"] <= 4)

    def test_generate_questions_empty_count(self):
        # بررسی حالت تعداد صفر
        questions = generate_questions("any", 10, 0)
        self.assertEqual(len(questions), 0)


if __name__ == "__main__":
    unittest.main()
