#!/usr/bin/env perl
# Verificación documental local, sin LLM, sin publicación y sin modificar fuentes.
use strict;
use warnings;
use utf8;
use open qw(:std :encoding(UTF-8));
use FindBin qw($RealBin);
use File::Temp qw(tempdir);
use File::Compare qw(compare);
use JSON::PP qw(decode_json);
use Encode qw(decode);

sub read_utf8 {
    my ($path) = @_;
    open my $fh, '<:encoding(UTF-8)', $path or die "No se puede leer $path: $!\n";
    local $/;
    return <$fh>;
}

sub check ($$) {
    my ($ok, $message) = @_;
    die "FALLO: $message\n" unless $ok;
    print "OK: $message\n";
}

sub command_text {
    my (@command) = @_;
    open my $fh, '-|', @command or die "No se pudo ejecutar $command[0]: $!\n";
    binmode $fh, ':encoding(UTF-8)';
    local $/;
    my $text = <$fh>;
    close $fh or die "Falló $command[0]\n";
    return $text // '';
}

sub normalized {
    my ($text, $latex) = @_;
    if ($latex) {
        $text =~ s/\\begin\{enumerate\}\[[^\]]*\]//g;
        $text =~ s/\\end\{enumerate\}//g;
        my $item = 0;
        $text =~ s/\\item\s*/++$item . '. '/ge;
        $text =~ s/\\(?:textbf|textit|fororef)\{//g;
        $text =~ s/\\,|~/ /g;
        $text =~ s/\\%/%/g;
        $text =~ s/--/–/g;
        $text =~ s/[{}]//g;
        die "Macro no contemplada en el cotejo del producto\n" if $text =~ /\\/;
    }
    $text =~ s/\s+/ /g;
    $text =~ s/^ | $//g;
    return $text;
}

my $stem = 'reporte-fundamentos-de-gestion-administrativa-Actividad-7';
my $tex = read_utf8("$RealBin/$stem.tex");
my $bib = read_utf8("$RealBin/fundamentos-de-gestion-administrativa.bib");
my @sections = $tex =~ /\\section\{([^}]+)\}/g;
check(join('|', @sections) eq 'Introducción|Del diagnóstico a la revisión de las decisiones|Conclusiones', 'Tres actos y desarrollo temático único');
check($tex =~ /\\clearpage\s*\\section\{Conclusiones\}/, 'Conclusiones en página nueva');
check($tex =~ /\\footnote\{Se utilizó GitHub Copilot/ && $tex !~ /\\section\*?\{[^}]*inteligencia artificial/i, 'Declaración de IA como nota al pie');
check($tex =~ /Actividad 7 - Fundamentos de Gestión Administrativa/, 'Subject de la actividad correcto');
check($tex =~ /style=apa/ && $tex =~ /backend=biber/, 'Bibliografía configurada con BibLaTeX-APA y Biber');

my @boxes = $tex =~ /\\begin\{forobox\}\{[^}]*\}(.*?)\\end\{forobox\}/sg;
my @txt = ('foro-participacion-Actividad-7.txt', 'foro-respuesta-1-Actividad-7.txt', 'foro-respuesta-2-Actividad-7.txt');
check(@boxes == 3, 'Tres cajas de producto independientes');
my @buttons = $tex =~ /\\foroCopyButton(?:\[[^\]]*\])?\{([^}]+)\}/g;
check(join('|', @buttons) eq join('|', @txt), 'Tres botones enlazados a los TXT correctos');
for my $i (0 .. 2) {
    my $expected = normalized(read_utf8("$RealBin/$txt[$i]"), 0);
    my $actual = normalized($boxes[$i], 1);
    if ($actual ne $expected) {
        my $at = 0;
        ++$at while $at < length($actual) && $at < length($expected) && substr($actual, $at, 1) eq substr($expected, $at, 1);
        die "Divergencia caja/TXT $txt[$i] en carácter $at:\nTEX: " . substr($actual, $at, 100) . "\nTXT: " . substr($expected, $at, 100) . "\n";
    }
    check(1, "Equivalencia literal normalizada caja/TXT: $txt[$i]");
    check($actual =~ /Referencia/ && $actual =~ /¿.+\?/, "Referencias y pregunta de diálogo en caja " . ($i + 1));
}

my %keys;
while ($tex =~ /\\cite[pt](?:\[[^\]]*\])*\{([^}]+)\}/g) { $keys{$_} = 1 for split /,/, $1; }
check(keys(%keys) == 3, 'Tres fuentes distintas citadas en el contenedor');
for my $key (sort keys %keys) {
    my @entries = $bib =~ /\@\w+\{\Q$key\E,/g;
    check(@entries == 1, "Entrada bibliográfica única: $key");
}

my $source = "$RealBin/referencias-fundamentos-de-gestion-administrativa/unidad-3-toma-de-decisiones/canos-y-colaboradores-toma-decisiones-empresa-proceso-clasificacion.pdf";
my $source_text = normalized(command_text('pdftotext', '-f', '5', '-l', '5', $source, '-'), 0);
my $quote = 'podemos obtener una respuesta adecuada para un problema equivocado';
check(index($source_text, $quote) >= 0, 'Cita textual localizada en la quinta página del PDF fuente');
check(index(normalized($boxes[0], 1), "«$quote» (Canós Darós et al., s. f., p. 5)") >= 0, 'Cita textual y localizador presentes en el producto');

my $extraction = "$RealBin/extractor-aulatex/conceptos-fundamentos-de-gestion-administrativa-actividad-7";
for my $name (qw(fichas_conceptos conceptos_detectados ideas_detectadas trazabilidad_fuentes resumen_planeacion)) {
    my $json = read_utf8("$extraction/$name.json");
    JSON::PP->new->decode($json);
    check(1, "Artefacto de extracción parseable: $name.json");
}

my $pdf = "$RealBin/$stem.pdf";
check(-s $pdf, 'PDF existente y no vacío');
for my $path ("$RealBin/$stem.tex", map { "$RealBin/$_" } @txt) {
    my $name = $path =~ s{.*/}{}r;
    check((stat($pdf))[9] >= (stat($path))[9], "PDF posterior o igual a $name");
}
my $attachments = command_text('pdfdetach', '-list', $pdf);
check($attachments =~ /^3 embedded files/m, 'PDF con exactamente tres archivos adjuntos');
my $tmp = tempdir('aulatex-foro7-XXXXXX', TMPDIR => 1, CLEANUP => 1);
for my $name (@txt) {
    my ($number) = $attachments =~ /^(\d+):.*\Q$name\E\s*$/m;
    check(defined $number, "Adjunto localizable: $name");
    system('pdfdetach', '-save', $number, '-o', "$tmp/$name", $pdf) == 0 or die "Error al extraer $name\n";
    check(compare("$tmp/$name", "$RealBin/$name") == 0, "Adjunto idéntico byte a byte: $name");
}
my $pdf_text = command_text('pdftotext', '-layout', $pdf, '-');
check($pdf_text !~ /\[\?\]|act7CanosSF|act7Lopez2020|act7Solano2003|PENDIENTE/, 'PDF sin claves de cita sin resolver ni marcadores pendientes');
my @pages = split /\f/, $pdf_text;
my @conclusion = grep { /\bConclusiones\b/ } @pages;
check(@conclusion == 1 && $conclusion[0] =~ /^\s*3\.\s+Conclusiones/s && $conclusion[0] =~ /antes de publicar/s, 'Conclusiones y nota de IA completas en una sola página');
check($pdf_text =~ /Versión para revisión/ && $tex !~ /Participación publicada en el foro/, 'Preparación diferenciada de publicación');
print "VALIDACIÓN DOCUMENTAL LOCAL SUPERADA. No certifica publicación, revisión personal ni ejecución integral del motor.\n";