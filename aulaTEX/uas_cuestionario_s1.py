"""Run the authorized S1 quiz while retaining a local academic record."""
from datetime import datetime, timezone
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from aulaTEX.aulatex.config import load_aulatex_env
from aulaTEX.uas_course_inspect import BASE_URL, _credentials


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "UAS/licenciatura-en-contaduria-uas/herramientas-digitales/referencias-herramientas-digitales/notas-herramientas-digitales/cuestionario-S1"
    output.mkdir(exist_ok=True)
    load_aulatex_env()
    credentials = _credentials(root)
    record = {"module": 50103, "started_utc": datetime.now(timezone.utc).isoformat(), "pages": [], "actions": [], "submitted": False}
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL + "/login/index.php", wait_until="domcontentloaded")
        page.locator("#username").fill(credentials["username"])
        page.locator("#password").fill(credentials["password"])
        page.locator("#loginbtn").click()
        page.wait_for_load_state("domcontentloaded")
        del credentials
        page.goto(BASE_URL + "/mod/quiz/view.php?id=50103", wait_until="domcontentloaded")
        page.get_by_role("button", name="Intentar examen", exact=True).click()
        if page.get_by_role("button", name="Comenzar intento", exact=True).count():
            page.get_by_role("button", name="Comenzar intento", exact=True).click()
        while True:
            page.wait_for_load_state("domcontentloaded")
            questions = page.locator(".que").evaluate_all("""elements => elements.map(element => ({
                id:element.id,text:element.innerText,
                fields:Array.from(element.querySelectorAll('input,select,textarea')).map(field=>({
                    id:field.id,name:field.name,type:field.type,value:field.type==='radio'?field.value:'',
                    options:field.tagName==='SELECT'?Array.from(field.options).map(option=>({text:option.text,value:option.value})):[]
                }))
            }))""")
            snapshot = {"text": page.locator("#region-main").inner_text(), "questions": questions, "buttons": page.locator("#region-main button,#region-main input[type=submit],#region-main a.btn").evaluate_all("elements=>elements.map(element=>({text:element.innerText||element.value,name:element.name}))")}
            record["pages"].append(snapshot)
            (output / "registro.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(snapshot, ensure_ascii=True), flush=True)
            command = json.loads(input("QUIZ_ACTION_JSON> "))
            if command.get("stop"):
                break
            for answer in command.get("answers", []):
                field = page.locator('[id="' + answer["id"] + '"]')
                if answer.get("check"):
                    field.check()
                elif "select" in answer:
                    field.select_option(answer["select"])
                else:
                    field.fill(answer["text"])
            record["actions"].append(command)
            if command.get("button"):
                button = page.get_by_role("button", name=command["button"], exact=True)
                if not button.count():
                    button = page.get_by_role("link", name=command["button"], exact=True)
                button.click()
            if command.get("submit"):
                record["submitted"] = True
            if command.get("finish"):
                record["final_text"] = page.locator("#region-main").inner_text()
                record["finished_utc"] = datetime.now(timezone.utc).isoformat()
                (output / "registro.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps({"final_text":record["final_text"]}, ensure_ascii=True), flush=True)
                break
        browser.close()


if __name__ == "__main__":
    main()