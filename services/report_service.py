from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from services.history_service import HistoryService


class ReportService:
    SLOT_LABELS = {
        "pre_market": "08:20 장전 전략",
        "opening": "09:10 장초반",
        "midday": "11:30 오전장",
        "afternoon": "14:10 오후",
        "closing": "15:15 마감 직전",
    }

    def __init__(self, history: HistoryService, output_dir: str | Path = "reports") -> None:
        self.history = history
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def previous_month(reference: date) -> tuple[date, date]:
        first_this_month = reference.replace(day=1)
        end = first_this_month - timedelta(days=1)
        start = end.replace(day=1)
        return start, end

    @staticmethod
    def _float(row: dict[str, str], key: str) -> float:
        try:
            return float(row.get(key, "0") or 0)
        except ValueError:
            return 0.0

    def calculate_metrics(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        total = len(rows)
        hits = sum(row["result"] == "HIT" for row in rows)
        by_signal: dict[str, list[dict[str, str]]] = defaultdict(list)
        by_slot: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_signal[row.get("signal_code", "UNKNOWN")].append(row)
            by_slot[row.get("slot", "unknown")].append(row)

        def stats(items: list[dict[str, str]]) -> dict[str, Any]:
            count = len(items)
            hit = sum(item["result"] == "HIT" for item in items)
            returns = [self._float(item, "return_after_signal") for item in items]
            return {
                "count": count,
                "hits": hit,
                "hit_rate": round(hit / count * 100, 1) if count else 0.0,
                "avg_return": round(sum(returns) / count, 3) if count else 0.0,
            }

        slot_stats = {key: stats(value) for key, value in by_slot.items()}
        signal_stats = {key: stats(value) for key, value in by_signal.items()}
        best_slot = max(slot_stats, key=lambda key: slot_stats[key]["hit_rate"], default="-")
        worst_slot = min(slot_stats, key=lambda key: slot_stats[key]["hit_rate"], default="-")
        miss_streak = 0
        max_miss_streak = 0
        for row in sorted(rows, key=lambda item: item.get("run_at", "")):
            miss_streak = miss_streak + 1 if row["result"] == "MISS" else 0
            max_miss_streak = max(max_miss_streak, miss_streak)

        score_bands: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            score = int(float(row.get("score", "50") or 50))
            if score <= 30:
                band = "0-30"
            elif score <= 45:
                band = "31-45"
            elif score <= 64:
                band = "46-64"
            elif score <= 79:
                band = "65-79"
            else:
                band = "80-100"
            score_bands[band].append(row)

        return {
            "total": total,
            "hits": hits,
            "hit_rate": round(hits / total * 100, 1) if total else 0.0,
            "signal_stats": signal_stats,
            "slot_stats": slot_stats,
            "score_stats": {key: stats(value) for key, value in score_bands.items()},
            "best_slot": best_slot,
            "worst_slot": worst_slot,
            "max_miss_streak": max_miss_streak,
            "signal_counts": dict(Counter(row.get("signal_code", "UNKNOWN") for row in rows)),
        }

    def _register_fonts(self) -> tuple[str, str]:
        candidates = [
            ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ]
        for regular, bold in candidates:
            if Path(regular).exists() and Path(bold).exists():
                pdfmetrics.registerFont(TTFont("MPRegular", regular))
                pdfmetrics.registerFont(TTFont("MPBold", bold))
                return "MPRegular", "MPBold"
        pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
        return "HYSMyeongJo-Medium", "HYSMyeongJo-Medium"

    def generate(self, start: date, end: date) -> tuple[Path, Path, str]:
        rows = self.history.rows_for_period(start, end)
        metrics = self.calculate_metrics(rows)
        period = f"{start:%Y%m%d}_{end:%Y%m%d}"
        pdf_path = self.output_dir / f"MarketPilot_monthly_{period}.pdf"
        csv_path = self.output_dir / f"MarketPilot_monthly_detail_{period}.csv"

        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=HistoryService.FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        regular, bold = self._register_fonts()
        styles = getSampleStyleSheet()
        title = ParagraphStyle("TitleKR", parent=styles["Title"], fontName=bold, fontSize=20, leading=25, alignment=TA_CENTER)
        heading = ParagraphStyle("HeadingKR", parent=styles["Heading2"], fontName=bold, fontSize=13, leading=18, spaceBefore=10)
        body = ParagraphStyle("BodyKR", parent=styles["BodyText"], fontName=regular, fontSize=9.5, leading=14)
        small = ParagraphStyle("SmallKR", parent=body, fontSize=8, leading=11)

        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
        story: list[Any] = [
            Paragraph("MarketPilot 월간 점검보고서", title),
            Spacer(1, 4*mm),
            Paragraph(f"분석 기간: {start:%Y-%m-%d} ~ {end:%Y-%m-%d}", body),
            Paragraph("본 보고서는 저장된 모의 신호의 사후 성과를 점검하며 실제 투자 성과를 보장하지 않습니다.", small),
            Spacer(1, 5*mm),
        ]

        summary_data = [
            ["평가 신호", "적중", "전체 적중률", "최대 연속 실패"],
            [str(metrics["total"]), str(metrics["hits"]), f"{metrics['hit_rate']:.1f}%", str(metrics["max_miss_streak"])],
        ]
        table = Table(summary_data, colWidths=[40*mm]*4)
        table.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,0), bold), ("FONTNAME", (0,1), (-1,-1), regular),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E9EEF6")),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ]))
        story += [table, Paragraph("시간대별 성과", heading)]

        slot_data = [["시간대", "신호 수", "적중률", "신호 후 평균 등락률"]]
        for slot in ["pre_market", "opening", "midday", "afternoon", "closing"]:
            stat = metrics["slot_stats"].get(slot, {"count":0,"hit_rate":0,"avg_return":0})
            slot_data.append([self.SLOT_LABELS[slot], stat["count"], f"{stat['hit_rate']:.1f}%", f"{stat['avg_return']:+.3f}%"])
        slot_table = Table(slot_data, colWidths=[55*mm, 28*mm, 34*mm, 48*mm])
        slot_table.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,0), bold), ("FONTNAME", (0,1), (-1,-1), regular),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E9EEF6")), ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
            ("ALIGN", (1,0), (-1,-1), "CENTER"), ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story += [slot_table, Paragraph("신호 유형별 성과", heading)]

        signal_names = {"LEVERAGE":"레버리지/상승", "INVERSE":"인버스/하락", "HOLD":"관망"}
        sig_data = [["신호", "신호 수", "적중률", "신호 후 평균 등락률"]]
        for code in ["LEVERAGE", "INVERSE", "HOLD"]:
            stat = metrics["signal_stats"].get(code, {"count":0,"hit_rate":0,"avg_return":0})
            sig_data.append([signal_names[code], stat["count"], f"{stat['hit_rate']:.1f}%", f"{stat['avg_return']:+.3f}%"])
        sig_table = Table(sig_data, colWidths=[55*mm, 28*mm, 34*mm, 48*mm])
        sig_table.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,0), bold), ("FONTNAME", (0,1), (-1,-1), regular),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E9EEF6")), ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
            ("ALIGN", (1,0), (-1,-1), "CENTER"), ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story += [sig_table, Paragraph("점검 결론", heading)]

        best = self.SLOT_LABELS.get(metrics["best_slot"], "자료 부족")
        worst = self.SLOT_LABELS.get(metrics["worst_slot"], "자료 부족")
        if metrics["total"] < 30:
            conclusion = "표본이 30건 미만이므로 결과는 초기 점검용으로만 해석해야 합니다."
        elif metrics["hit_rate"] >= 60:
            conclusion = "전체 적중률은 양호한 편이나, 거래비용과 슬리피지를 반영한 추가 검증이 필요합니다."
        else:
            conclusion = "현재 가중치의 예측력이 충분하지 않을 수 있어 시간대·신호별 가중치 재조정이 필요합니다."
        story += [
            Paragraph(f"- 가장 높은 적중률 시간대: {best}", body),
            Paragraph(f"- 가장 낮은 적중률 시간대: {worst}", body),
            Paragraph(f"- 종합 의견: {conclusion}", body),
            Spacer(1, 4*mm),
            Paragraph("유의사항", heading),
            Paragraph("적중률은 방향성 기준이며 세금, 수수료, 슬리피지, 체결 가능성 및 레버리지 상품의 추적 오차를 반영하지 않습니다.", small),
        ]
        doc.build(story)

        summary = (
            f"📊 MarketPilot 월간 점검보고서\n"
            f"기간 : {start:%Y-%m-%d} ~ {end:%Y-%m-%d}\n\n"
            f"평가 신호 : {metrics['total']}건\n"
            f"전체 적중률 : {metrics['hit_rate']:.1f}%\n"
            f"최고 성과 시간대 : {best}\n"
            f"개선 필요 시간대 : {worst}\n"
            f"최대 연속 실패 : {metrics['max_miss_streak']}회\n\n"
            f"PDF 보고서와 상세 CSV를 함께 첨부합니다."
        )
        return pdf_path, csv_path, summary
