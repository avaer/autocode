import os
from core.utils import is_runnable, log, read_code, strip_header, compose_header, save_code, run_code

def coalesce(filename, code, previous_code, goal, reasoning):
    log(filename, "COALESCING OUTPUT STATE WITH PREVIOUS STATE")

    code_backup = code
    code = strip_header(code)
    previous_code = strip_header(previous_code)

    code_lines = code.split("\n")
    previous_code_lines = previous_code.split("\n")

    # find footer in the code
    footer_line = next((line for line in code_lines if "__name__" in line), None)
    previous_footer_line = next((line for line in previous_code_lines if "__name__" in line), None)

    new_code_has_footer = footer_line is not None
    previous_code_has_footer = previous_footer_line is not None

    if new_code_has_footer:
        footer = "\n".join(code_lines[code_lines.index(footer_line) :])
    else:
        footer = None

    if previous_code_has_footer:
        previous_footer = "\n".join(previous_code_lines[previous_code_lines.index(previous_footer_line) :])
    else:
        previous_footer = None

    has_new_footer = new_code_has_footer and previous_code_has_footer and footer != previous_footer

    footer_snippet = None
    if has_new_footer:
        if "..." in footer:
            footer_snippet = footer.split("...")[1]
            if footer_snippet.strip() == "":
                footer_snippet = None
        elif code_lines.index(footer_line) < 4:
            footer_snippet = footer.split("\n")
        if footer_snippet is not None and footer_line in footer_snippet:
            footer_snippet = footer_snippet.split(footer_line)[1]

        if footer_snippet is not None:
            log(filename, "*** CONCATENING RESULT WITH PREVIOUS STATE")
            code = code + "\n" + footer_snippet
        else:
            code_lines = code_lines[: code_lines.index(footer_line)]
            code = "\n".join(code_lines) + "\n" + footer
            log(filename, "*** REPLACING TAIL OF PREVIOUS STATE WITH RESULT")
    elif new_code_has_footer is False and previous_code_has_footer is False:
        code = (
            code
            + "\n\nif __name__ == '__main__':\n    # TODO: ADD TESTS HERE\n    assert(False)"
        )
        log(filename, "*** ATTACHING INITIALIZATION TAIL TO PREVIOUS STATE")
    
    import_lines = [line for line in code.split("\n") if line.startswith("import")] + [
        line for line in code.split("\n") if line.startswith("from")
    ]
    import_lines = [
        line.split("as")[0].split("import")[1].split(".")[-1].strip()
        for line in import_lines
    ]

    previous_import_lines = [
        line for line in previous_code.split("\n") if line.startswith("import")
    ] + [line for line in previous_code.split("\n") if line.startswith("from")]
    previous_import_lines = [
        line.split("as")[0].split("import")[1].split(".")[-1].strip()
        for line in previous_import_lines
    ]

    new_code_has_imports = len(import_lines) > 0
    previous_code_has_imports = len(previous_import_lines) > 0

    if new_code_has_imports == False and previous_code_has_imports == False:
        log(filename, "*** COALESCENCE FAILED: NO HEADER INFORMATION DETECTED IN EITHER STATE")
        return {"code": code_backup, "new_imports": None, "success": False}

    new_imports = (
        new_code_has_imports == True and previous_code_has_imports == False
    )

    if (
        new_imports == False
        and new_code_has_imports == True
        and previous_code_has_imports == True
    ):
        new_imports = any(
            [import_line not in previous_import_lines for import_line in import_lines]
        )

    if new_imports == True:
        log(filename, "*** INTEGRATING STATE HEADERS")
        new_imports = set(import_lines)
        code_lines = [line for line in code_lines if not line.startswith("import")] + [
            line for line in code_lines if not line.startswith("from")
        ]
        for line in code_lines:
            for previous_import_line in previous_import_lines:
                if previous_import_line in line:
                    new_imports.add(previous_import_line)

        code_lines = list(new_imports) + code_lines
        code = "\n".join(code_lines)

    code = compose_header(goal, reasoning) + code
    
    # if there is a ... in the code, and it's not in a comment, then we probably lost some code
    if "..." in code and "#" not in code.split("...")[0]:
        log(filename, "*** COALESCENCE FAILED: CODE WAS LOST")
        return {
            "code": code_backup,
            "new_imports": new_imports,
            "success": False,
        }

    if(code == code_backup):
        log(filename, "*** COALESCENCE HAD NO RESULT, GENERATIONS ARE IDENTICAL")
        return {"code": code, "new_imports": new_imports, "success": False}
    if(code != code_backup):
        log(filename, "*** COALESCENCE SUCCEEDED")

    return {"code": code, "new_imports": new_imports, "success": True}

if __name__ == "__main__":
    def create_test_file(filename, imports, footer):
        with open(filename, 'w') as f:
            f.write(imports + '\n\n' + footer)
    # Test 1
    print("Running Test 1...")
    imports = 'import os\nimport sys'
    footer = 'if __name__ == "__main__":\n    print("Hello, World!")'
    create_test_file("old.py", imports, footer)
    create_test_file("new.py", imports, footer)

    result = coalesce("test1", read_code("new.py"), read_code("old.py"), "goal", "reasoning")
    assert result["success"] == True, f"Test 1 failed with {result}"

    # Test 2
    print("Running Test 2...")
    new_imports = 'import os\nimport sys\nimport math'
    new_footer = 'if __name__ == "__main__":\n    print("Hello, Universe!")'
    create_test_file("new.py", new_imports, new_footer)

    result = coalesce("test2", read_code("new.py"), read_code("old.py"), "goal", "reasoning")
    assert result["success"] == True, f"Test 2 failed with {result}"

    # Test 3
    print("Running Test 3...")
    create_test_file("old.py", '', '')
    create_test_file("new.py", '', '')

    result = coalesce("test3", read_code("new.py"), read_code("old.py"), "goal", "reasoning")
    assert result["success"] == False, f"Test 3 failed with {result}"

    # Test 4
    print("Running Test 4...")
    create_test_file("old.py", '', '')
    create_test_file("new.py", 'import os', footer)

    result = coalesce("test4", read_code("new.py"), read_code("old.py"), "goal", "reasoning")
    assert result["success"] == True, f"Test 4 failed with {result}"

    # Test 5
    print("Running Test 5...")
    create_test_file("old.py", '', footer)
    create_test_file("new.py", imports, footer)

    result = coalesce("test5", read_code("new.py"), read_code("old.py"), "goal", "reasoning")
    assert result["success"] == True, f"Test 5 failed with {result}"

    # Cleanup
    os.remove("old.py")
    os.remove("new.py")
    print("All tests passed!")
