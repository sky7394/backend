import json

async def generate_questions(topic: str, grade: str, count: int):
    questions = []

    for i in range(1, count + 1):
        questions.append({
            "question": f"سوال {i} از مبحث {topic} برای پایه {grade} چیست؟",
            "options": [
                "گزینه 1",
                "گزینه 2",
                "گزینه 3",
                "گزینه 4"
            ],
            "answer": "گزینه 1"
        })

    return json.dumps({"questions": questions}, ensure_ascii=False)
