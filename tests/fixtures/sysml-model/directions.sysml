package Directions {
          port def Signal { attribute level : Real; }

          part def Directions {
            in port a : Signal;
            out port b : Signal;
            inout port c : Signal;
            port plain : Signal;
          }
        }
