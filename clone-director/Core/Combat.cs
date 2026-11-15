namespace CloneDirector.Core;

public static class Combat
{
    // An initial tuning value, in Source engine distance units. Not a line-of-sight test.
    public const float NearbyShotRadius = 1200;
    public static bool Nearby(float ax, float ay, float az, float bx, float by, float bz) =>
        (ax - bx) * (ax - bx) + (ay - by) * (ay - by) + (az - bz) * (az - bz) <= NearbyShotRadius * NearbyShotRadius;
}
