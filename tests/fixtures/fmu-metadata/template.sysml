package Example {
      $marker

      $concrete

      part def Comp {
        $part_body
      }

      part def $COMPOSITION_NAME {
        part comp : Comp;
      }
    }
