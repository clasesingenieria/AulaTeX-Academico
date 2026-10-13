"""Valida los pasos algebraicos de Cálculo Integral, Actividad 3.

Este archivo es una prueba técnica externa. Sus resultados no se incorporan al PDF.
"""

from collections.abc import Mapping
from typing import Any

import sympy as sp


x: Any = sp.Symbol("x", real=True)
A: Any = sp.Symbol("A")
B: Any = sp.Symbol("B")
ln: Any = sp.log

checks_run = 0
failures: list[str] = []


def check_zero(label: str, expression: Any) -> None:
    """Comprueba que una diferencia simbólica sea idénticamente cero."""
    global checks_run
    checks_run += 1
    result = sp.factor(sp.cancel(sp.together(expression)))
    if result != 0:
        failures.append(f"{label}: diferencia = {result}")


def check_solution(
    label: str,
    equations: list[Any],
    expected: Mapping[Any, Any],
) -> None:
    """Comprueba la solución exacta de un sistema de coeficientes."""
    global checks_run
    checks_run += 1
    solution = sp.solve(equations, (A, B), dict=True)
    if solution != [dict(expected)]:
        failures.append(f"{label}: solución = {solution}, esperada = {dict(expected)}")


def validate_exercise_7() -> None:
    denominator = x**2 - 9
    factored = (x - 3) * (x + 3)
    integrand = 1 / denominator
    partial = sp.Rational(1, 6) / (x - 3) - sp.Rational(1, 6) / (x + 3)
    antiderivative = sp.Rational(1, 6) * ln(x - 3) - sp.Rational(1, 6) * ln(x + 3)

    check_zero("7.1 factorización", denominator - factored)
    cleared = sp.cancel((integrand - A / (x - 3) - B / (x + 3)) * factored)
    check_zero("7.2 eliminación de denominadores", cleared - (1 - A * (x + 3) - B * (x - 3)))
    check_solution("7.3 sistema de coeficientes", [A + B, 3 * A - 3 * B - 1], {A: sp.Rational(1, 6), B: -sp.Rational(1, 6)})
    check_zero("7.4 fracciones parciales", integrand - partial)
    check_zero("7.5 integral de 1/(x-3)", sp.diff(ln(x - 3), x) - 1 / (x - 3))
    check_zero("7.6 integral de 1/(x+3)", sp.diff(ln(x + 3), x) - 1 / (x + 3))
    check_zero("7.7 antiderivada final", sp.diff(antiderivative, x) - integrand)


def validate_exercise_8() -> None:
    denominator = 4 * x**2 - 1
    factored = (2 * x - 1) * (2 * x + 1)
    integrand = 1 / denominator
    partial = sp.Rational(1, 2) / (2 * x - 1) - sp.Rational(1, 2) / (2 * x + 1)
    antiderivative = sp.Rational(1, 4) * ln(2 * x - 1) - sp.Rational(1, 4) * ln(2 * x + 1)

    check_zero("8.1 factorización", denominator - factored)
    cleared = sp.cancel((integrand - A / (2 * x - 1) - B / (2 * x + 1)) * factored)
    check_zero("8.2 eliminación de denominadores", cleared - (1 - A * (2 * x + 1) - B * (2 * x - 1)))
    check_solution("8.3 sistema de coeficientes", [2 * A + 2 * B, A - B - 1], {A: sp.Rational(1, 2), B: -sp.Rational(1, 2)})
    check_zero("8.4 fracciones parciales", integrand - partial)
    check_zero("8.5 sustitución u=2x-1", sp.diff(ln(2 * x - 1) / 2, x) - 1 / (2 * x - 1))
    check_zero("8.6 sustitución v=2x+1", sp.diff(ln(2 * x + 1) / 2, x) - 1 / (2 * x + 1))
    check_zero("8.7 antiderivada final", sp.diff(antiderivative, x) - integrand)


def validate_exercise_9() -> None:
    denominator = x**2 + 3 * x - 4
    factored = (x + 4) * (x - 1)
    integrand = 5 / denominator
    partial = -1 / (x + 4) + 1 / (x - 1)
    antiderivative = -ln(x + 4) + ln(x - 1)

    check_zero("9.1 factorización", denominator - factored)
    cleared = sp.cancel((integrand - A / (x + 4) - B / (x - 1)) * factored)
    check_zero("9.2 eliminación de denominadores", cleared - (5 - A * (x - 1) - B * (x + 4)))
    check_solution(
        "9.3 sistema de coeficientes",
        [A + B, -A + 4 * B - 5],
        {A: sp.Integer(-1), B: sp.Integer(1)},
    )
    check_zero("9.4 fracciones parciales", integrand - partial)
    check_zero("9.5 integral de -1/(x+4)", sp.diff(-ln(x + 4), x) + 1 / (x + 4))
    check_zero("9.6 integral de 1/(x-1)", sp.diff(ln(x - 1), x) - 1 / (x - 1))
    check_zero("9.7 antiderivada final", sp.diff(antiderivative, x) - integrand)


def validate_exercise_10() -> None:
    denominator = x**2 + 11 * x + 18
    factored = (x + 2) * (x + 9)
    integrand = (x + 2) / denominator
    simplified = 1 / (x + 9)
    antiderivative = ln(x + 9)

    check_zero("10.1 factorización", denominator - factored)
    cleared = sp.cancel((integrand - A / (x + 2) - B / (x + 9)) * factored)
    check_zero("10.2 eliminación de denominadores", cleared - (x + 2 - A * (x + 9) - B * (x + 2)))
    check_solution(
        "10.3 sistema de coeficientes",
        [A + B - 1, 9 * A + 2 * B - 2],
        {A: sp.Integer(0), B: sp.Integer(1)},
    )
    check_zero("10.4 fracciones parciales", integrand - simplified)
    check_zero("10.5 cancelación en el dominio", (x + 2) - simplified * factored)
    check_zero("10.6 sustitución u=x+9", sp.diff(ln(x + 9), x) - simplified)
    check_zero("10.7 antiderivada final", sp.diff(antiderivative, x) - integrand)


def main() -> None:
    validate_exercise_7()
    validate_exercise_8()
    validate_exercise_9()
    validate_exercise_10()

    if failures:
        print(f"Fallaron {len(failures)} de {checks_run} comprobaciones:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print(f"Actividad 3: {checks_run}/{checks_run} pasos simbólicos correctos.")


if __name__ == "__main__":
    main()