# AulaTeX-Academico latexmk configuration.
# Keep builds reproducible across Codex, VS Code LaTeX Workshop and TeXstudio.

use Cwd qw(getcwd);
use File::Spec;
use Config;

my $project_root = getcwd();
my $path_sep = $Config::Config{path_sep} || ($^O =~ /MSWin32/i ? ';' : ':');

sub aulatex_path {
    my ($path, $recursive) = @_;
    my $full = File::Spec->rel2abs($path, $project_root);
    $full =~ s!\\!/!g;
    return $recursive ? "$full//" : $full;
}

sub prepend_env_paths {
    my ($name, @paths) = @_;
    my $prefix = join($path_sep, @paths);
    # A trailing separator preserves TeX's built-in search path (TEXMF trees)
    # while still preferring the repository-specific directories first.
    $ENV{$name} = defined $ENV{$name} && length $ENV{$name}
        ? "$prefix$path_sep$ENV{$name}$path_sep"
        : "$prefix$path_sep";
}

$pdf_mode = 1;
$recorder = 1;
$interaction = 'nonstopmode';
$emulate_aux = 1;
$max_repeat = 5;

$out_dir = '.build/latex';
$aux_dir = '.build/latex/aux';
# Keep diagnostics visible for AulaTeX agents and stop immediately on hard errors.
$pdflatex = 'pdflatex -halt-on-error -interaction=nonstopmode -file-line-error %O %S';
$bibtex = 'bibtex %O %B';

prepend_env_paths('TEXINPUTS',
    aulatex_path('.', 0),
    aulatex_path('aulaTEX/base/Plantilla-Informe', 1),
    aulatex_path('aulaTEX/base/Plantilla-Informe/src', 1),
    aulatex_path('aulaTEX/base/Plantilla-Informe/img', 1),
    aulatex_path('aulaTEX/base/latex', 1),
    aulatex_path('base', 1),
    aulatex_path('UnADM', 1),
    aulatex_path('UAS', 1),
    aulatex_path('UCNL', 1),
    aulatex_path('UANL', 1),
    aulatex_path('IIIEPE', 1),
    aulatex_path('ITESCA', 1)
);

# Keep bibliography lookup explicit enough to avoid stale archived copies
# (for example other templates with the same jobname `main` or `library.bib`).
prepend_env_paths('BIBINPUTS',
    aulatex_path('.', 0),
    aulatex_path('aulaTEX/base/Plantilla-Informe', 1),
    aulatex_path('UnADM', 1),
    aulatex_path('UAS', 1),
    aulatex_path('UCNL', 1),
    aulatex_path('UANL', 1),
    aulatex_path('IIIEPE', 1),
    aulatex_path('ITESCA', 1)
);

prepend_env_paths('BSTINPUTS',
    aulatex_path('.', 0),
    aulatex_path('aulaTEX/base/Plantilla-Informe/bibtex', 1),
    aulatex_path('aulaTEX/base/Plantilla-Informe', 1)
);

$clean_ext = 'aux bbl bcf blg fdb_latexmk fls lof log lot nav out run.xml snm synctex.gz toc vrb xdv';
