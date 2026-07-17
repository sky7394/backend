import random

def generate_questions(topic, grade, count):

    questions = []

    for i in range(count):
        q = {
            "question": f"سوال {i+1} از درس {topic} پایه {grade}",
            "options": [
                "گزینه ۱",
                "گزینه ۲",
                "گزینه ۳",
                "گزینه ۴"
            ],
            "answer": random.randint(1,4)
        }

        questions.append(q)

    return questions
