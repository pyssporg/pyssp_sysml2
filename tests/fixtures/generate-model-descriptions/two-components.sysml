package Example {
          port def Status {
            attribute ok: Boolean;
          }

          part def Sensor {
            out port status : Status;
          }

          part def Controller {
            in port status : Status;
          }

          part def $COMPOSITION_NAME {
            part sensor : Sensor;
            part controller : Controller;
          }
        }
