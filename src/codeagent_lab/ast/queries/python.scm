; query:def
(function_definition
  name: (identifier) @definition.name
)

(class_definition
  name: (identifier) @definition.name
)

; query:ref
(call
  function: (identifier) @reference.name
)

(call
  function: (attribute
    attribute: (identifier) @reference.name
  )
)
