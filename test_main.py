"""날짜 계산 검증 테스트 (python -m unittest test_main -v)
기대값은 main.py와 별개로 달력 계산으로 정했습니다."""
import inspect
import unittest
from datetime import date

import main

B = "2025-03-15"


class DateMath(unittest.TestCase):
    def test_add_months_clamp(self):
        self.assertEqual(main.add_months(date(2025, 1, 31), 1), date(2025, 2, 28))
        self.assertEqual(main.add_months(date(2024, 1, 31), 1), date(2024, 2, 29))
        self.assertEqual(main.add_months(date(2025, 3, 15), 16), date(2026, 7, 15))

    def test_age_text(self):
        self.assertEqual(main.age_text(date(2025, 3, 15), date(2025, 10, 20)), "생후 7개월 5일")
        self.assertEqual(main.age_text(date(2025, 3, 15), date(2025, 10, 14)), "생후 6개월 29일")
        self.assertEqual(main.age_text(date(2020, 3, 15), date(2026, 5, 20)), "만 6세 2개월")
        self.assertIn("출생 예정일까지 10일", main.age_text(date(2025, 3, 15), date(2025, 3, 5)))

    def test_windows(self):
        b = date(2025, 3, 15)
        s, e, p = main.window(b, ("point", 2))
        self.assertEqual((s, e, p), (date(2025, 5, 15), date(2025, 5, 15), True))
        s, e, _ = main.window(b, ("range", 12, 15))   # 12개월 도달일 ~ 15개월이 끝나는 날
        self.assertEqual((s, e), (date(2026, 3, 15), date(2026, 7, 14)))
        s, e, _ = main.window(b, ("range", 4, 6))
        self.assertEqual((s, e), (date(2025, 7, 15), date(2025, 10, 14)))
        s, e, _ = main.window(b, ("days", 14, 35))
        self.assertEqual((s, e), (date(2025, 3, 29), date(2025, 4, 19)))
        s, e, _ = main.window(b, ("range", 66, 71))
        self.assertEqual((s, e), (date(2030, 9, 15), date(2031, 3, 14)))


class Vaccination(unittest.TestCase):
    def test_now_section_at_2_months(self):
        r = main.get_vaccination_schedule(B, "2025-05-20")
        now = r.split("【지금 해당하는 시기】")[1].split("【")[0]
        self.assertIn("DTaP 1차", now)
        self.assertIn("2025.5.15 도달", now)
        self.assertNotIn("MMR", now)

    def test_soon_and_lookahead(self):
        r = main.get_vaccination_schedule(B, "2026-02-20", 30)    # 12개월(2026.3.15) 시작 23일 전
        soon = r.split("【30일 이내 시작】")[1].split("【")[0]
        self.assertIn("MMR 1차", soon)
        self.assertIn("2026.3.15 ~ 2026.7.14", soon)
        r2 = main.get_vaccination_schedule(B, "2026-02-20", 10)
        self.assertNotIn("MMR 1차", r2.split("【10일 이내 시작】")[1].split("【")[0])

    def test_past_and_footer(self):
        r = main.get_vaccination_schedule(B, "2027-01-10")
        self.assertIn("표준 시기가 지난 항목", r)
        self.assertIn("예방접종도우미", r)
        self.assertIn("의료 자문이 아닙니다", r)

    def test_unborn_and_defaults(self):
        r = main.get_vaccination_schedule("2026-12-01", "2026-11-02")   # 출생 예정일
        self.assertIn("출생 예정일까지 29일", r)
        self.assertIn("B형간염 1차", r)

    def test_invalid(self):
        self.assertTrue(main.get_vaccination_schedule("2025/03/15").startswith("[입력 확인]"))
        self.assertTrue(main.get_vaccination_schedule("2025-02-30").startswith("[입력 확인]"))
        self.assertTrue(main.get_vaccination_schedule("2030-01-01", "2026-11-02").startswith("[입력 확인]"))
        self.assertTrue(main.get_vaccination_schedule("2000-01-01", "2026-11-02").startswith("[입력 확인]"))
        self.assertTrue(main.get_vaccination_schedule(B, "bad").startswith("[입력 확인]"))


class Checkup(unittest.TestCase):
    def test_second_round_now(self):
        r = main.get_checkup_schedule(B, "2025-08-01")
        now = r.split("【지금 해당하는 시기】")[1].split("【")[0]
        self.assertIn("영유아 건강검진 2차", now)
        self.assertIn("2025.7.15 ~ 2025.10.14", now)

    def test_oral_and_total_rounds(self):
        r = main.get_checkup_schedule(B, "2026-09-20", 400)     # 18개월(2026.9.15) 도달 직후
        self.assertIn("영유아 구강검진(18~29개월)", r)
        self.assertIn("영유아 건강검진 4차", r)
        self.assertEqual(len(main.CHECKUPS), 8)
        self.assertEqual(len(main.ORAL), 4)

    def test_footer(self):
        r = main.get_checkup_schedule(B, "2025-08-01")
        self.assertIn("1577-1000", r)


class Checklist(unittest.TestCase):
    def test_combined_and_tags(self):
        r = main.get_upcoming_checklist(B, "2025-06-20", 60)    # 4개월(7.15) 시작 25일 전
        self.assertIn("(접종) DTaP 2차", r)
        self.assertIn("(검진) 영유아 건강검진 2차", r)
        self.assertIn("☐", r)

    def test_invalid(self):
        self.assertTrue(main.get_upcoming_checklist("x").startswith("[입력 확인]"))


class Reference(unittest.TestCase):
    def test_reference(self):
        r = main.get_schedule_reference()
        for s in ("2026-11-02", "2014년생", "nip.kdca.go.kr", "1577-1000", "의료 자문이 아닙니다"):
            self.assertIn(s, r)


class Registry(unittest.TestCase):
    def test_tools(self):
        import fastmcp
        reg = getattr(fastmcp, "REG", None)
        if reg is None:
            self.skipTest("등록 정보 검사는 테스트용 스텁 fastmcp에서만 실행합니다")
        self.assertEqual(set(reg), {"get_vaccination_schedule", "get_checkup_schedule",
                                    "get_upcoming_checklist", "get_schedule_reference"})
        for name, (kw, fn) in reg.items():
            self.assertEqual(set(kw["annotations"]),
                             {"title", "readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"})
            self.assertLessEqual(len(kw["description"]), 1024, name)
            self.assertIn("육아 일정 도우미 - Baby Schedule Helper", kw["description"])
            self.assertNotIn("kakao", name.lower())
            self.assertTrue(inspect.signature(fn).parameters is not None)


if __name__ == "__main__":
    unittest.main()
