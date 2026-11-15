namespace CloneDirector.Core;

public static class Combat
{
    // An initial tuning value, in Source engine distance units. Not a line-of-sight test.
    public const float NearbyShotRadius = 1200;
    // A route plays recorded inputs and never looks at enemies, so a clone could run into a fight and die
    // before any shot or damage stops it. Playback hands over to the bot base once an enemy is this close
    // (Source units, 3D, no line-of-sight test, so it also fires through walls). A starting value, to tune.
    public const float EnemyContactRadius = 900;
    public static bool EnemyClose(float ax, float ay, float az, float bx, float by, float bz) =>
        (ax - bx) * (ax - bx) + (ay - by) * (ay - by) + (az - bz) * (az - bz) <= EnemyContactRadius * EnemyContactRadius;
    public static bool Nearby(float ax, float ay, float az, float bx, float by, float bz) =>
        (ax - bx) * (ax - bx) + (ay - by) * (ay - by) + (az - bz) * (az - bz) <= NearbyShotRadius * NearbyShotRadius;
}
