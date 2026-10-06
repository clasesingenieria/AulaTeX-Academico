function Pandoc(doc)
  local course = pandoc.utils.stringify(doc.meta.course)
  local selected = false
  local omit_note = false
  local body = pandoc.List()
  for _, block in ipairs(doc.blocks) do
    if block.t == 'Header' and block.level == 2 then
      selected = pandoc.utils.stringify(block.content) == course
      omit_note = false
    elseif selected and block.t == 'Header' and block.level == 3 and pandoc.utils.stringify(block.content) == 'Retroalimentaciones' then
      omit_note = true
    elseif selected and not omit_note then
      if block.t == 'Header' then
        body:insert(pandoc.Para({pandoc.Strong(block.content)}))
      else
        body:insert(block)
      end
    end
  end
  if #body == 0 then
    error('No se encontro la materia en las propuestas de semana 1')
  end
  local output = pandoc.List({
    pandoc.RawBlock('latex', '\\section{Identificacion y estado}'),
    pandoc.Para({pandoc.Str('Propuesta de participacion basada en el proyecto, elaborada con apoyo de GitHub Copilot. Requiere revision personal; no publicada. No acredita conocimientos previos ni experiencias personales confirmadas. Edad y residencia, cuando se solicitan, permanecen pendientes.')}),
    pandoc.RawBlock('latex', '\\section{Participacion principal}\n\\begin{forobox}[title={Participacion principal -- propuesta no publicada}]')
  })
  for _, block in ipairs(body) do
    output:insert(block)
  end
  output:insert(pandoc.RawBlock('latex', '\\end{forobox}'))
  if course == 'Derecho penal especial mexicano' then
    output:insert(pandoc.RawBlock('latex', '\\section{Respuestas a participaciones}'))
    for number = 1, 2 do
      output:insert(pandoc.RawBlock('latex', '\\begin{forobox}[title={Respuesta ' .. number .. ' -- pendiente de intervencion real}]'))
      output:insert(pandoc.Para({pandoc.Str('Pendiente: seleccionar y leer una participacion real, identificar su idea central y redactar una retroalimentacion respetuosa y especifica. No se simula una respuesta publicada ni se atribuye una experiencia de otra persona al estudiante.')}))
      output:insert(pandoc.RawBlock('latex', '\\end{forobox}'))
    end
  else
    output:insert(pandoc.RawBlock('latex', '\\section{Respuestas y alcance}'))
    output:insert(pandoc.Para({pandoc.Str('No se agregan respuestas ficticias. La consigna consultada no exige replicas; Antecedentes indica expresamente que no es necesario responder a companeros. Si el docente solicita respuestas adicionales, deben documentarse en cajas independientes tras leer las intervenciones correspondientes.')}))
  end
  doc.blocks = output
  doc.meta.title = pandoc.MetaString('Foro de semana 1: ' .. course)
  return doc
end