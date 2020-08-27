import subprocess
import tempfile
import os
import pathlib

TEMPLATES = [
    ('a.ipynb', 'a'),
    ('b.ipynb', 'b'),
    ('c.ipynb', 'c'),
]


def _exec_update_notebooks(base_path, update_flag=True, bad_flag=False):
    # get path to real script
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        '..', '..', 'update_notebooks.sh')

    # configure args
    args = ["bash", os.path.abspath(path)]
    if update_flag:
        args.append("--update")
    if bad_flag:
        args.append("-g")

    # run subprocess from base_dir
    subprocess.check_call(args, cwd=base_path)


def _make_dir_and_exec(base_dir, templates, scripts=None, update_flag=True, bad_flag=False):
    os.mkdir(os.path.join(base_dir, "templates"))
    for template in templates:
        pathlib.Path(os.path.join(base_dir, "templates", template[0])).write_text(template[1])

    if scripts is not None:
        os.mkdir(os.path.join(base_dir, "scripts"))
        for script in scripts:
            pathlib.Path(os.path.join(base_dir, "scripts", script[0])).write_text(script[1])

    _exec_update_notebooks(base_dir, update_flag=update_flag, bad_flag=bad_flag)


def _assert_dir_structure(test_dir, structure):
    assert os.path.exists(test_dir)

    for name, contents in structure:
        assert os.path.exists(os.path.join(test_dir, name))
        assert (pathlib.Path(os.path.join(test_dir, name)).read_text() == contents)

    for filename in os.listdir(test_dir):
        matches = [name_cont for name_cont in structure if name_cont[0] == filename]
        assert (len(matches) == 1)
        assert (matches[0][1] == pathlib.Path(os.path.join(test_dir, filename)).read_text())


def _run_test(templates, scripts=None, output_no_update=None, output_update=None, bad_flag=False):
    with tempfile.TemporaryDirectory() as temp_dir:
        _make_dir_and_exec(temp_dir,
                           templates,
                           scripts=scripts,
                           update_flag=False,
                           bad_flag=bad_flag)

        _assert_dir_structure(os.path.join(temp_dir, 'scripts'),
                              output_no_update)

    with tempfile.TemporaryDirectory() as temp_dir:
        _make_dir_and_exec(temp_dir,
                           templates,
                           scripts=scripts,
                           update_flag=True,
                           bad_flag=bad_flag)

        _assert_dir_structure(os.path.join(temp_dir, 'scripts'),
                              output_update)


# test no script directory present
def test_no_script_dir():
    _run_test(TEMPLATES,
              output_no_update=TEMPLATES,
              output_update=TEMPLATES)


def test_no_notebooks():
    # scripts directory is created but not filled
    scripts = []

    _run_test(TEMPLATES,
              scripts=scripts,
              output_no_update=TEMPLATES,
              output_update=TEMPLATES)


# test scripts preservation on no-update
def test_no_vs_full_update():

    scripts = [
        ('a.ipynb', 'b'),
        ('b.ipynb', 'c'),
        ('c.ipynb', 'a'),
    ]

    _run_test(TEMPLATES,
              scripts=scripts,
              output_no_update=scripts,
              output_update=TEMPLATES)


def test_name_mismatches():

    scripts = [
        ('a.ipynb', 'b'),
        ('b.ipynb', 'c'),
        ('d.ipynb', 'd')
    ]

    _run_test(TEMPLATES,
              scripts=scripts,
              output_no_update=scripts + [TEMPLATES[-1]],
              output_update=TEMPLATES + [scripts[-1]])


def test_update_no_diff():
    _run_test(TEMPLATES,
              scripts=TEMPLATES,
              output_no_update=TEMPLATES,
              output_update=TEMPLATES)


def test_wrong_flag():
    _run_test(TEMPLATES,
              output_no_update=TEMPLATES,
              output_update=TEMPLATES,
              bad_flag=True)
