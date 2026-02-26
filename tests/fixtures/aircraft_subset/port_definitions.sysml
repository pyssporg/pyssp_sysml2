package Aircraft {
  port def PilotCommand {
    doc /* HOTAS-style control payload shared across control surfaces and mission computer consumers. */
    attribute stick_pitch_norm: Real;
    attribute stick_roll_norm: Real;
    attribute mode_switch: Integer;
  }

  port def OrientationEuler {
    doc /* Air vehicle orientation expressed as Euler angles in degrees. */
    attribute roll_deg: Real;
    attribute pitch_deg: Real;
    attribute yaw_deg: Real;
  }

  port def PositionXYZ {
    doc /* Local navigation frame expressed in kilometers (x=North, y=East, z=Up). */
    attribute x_km: Real;
    attribute y_km: Real;
    attribute z_km: Real;
  }

  port def FlightStatusPacket {
    doc /* Mission computer status feedback consumed by autonomy and analysis models. */
    attribute airspeed_mps: Real;
    attribute angle_of_attack_deg: Real;
    attribute health_code: Integer;
  }

  port def MissionStatus {
    doc /* Waypoint-tracking status produced by the autopilot for logging and requirement evaluation. */
    attribute waypoint_index: Integer;
    attribute total_waypoints: Integer;
    attribute complete: Boolean;
  }
}
