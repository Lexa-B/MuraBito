#pragma once

#include "CoreMinimal.h"

/** Zoom limits. Zoom01 = 0 is the near limit, 1 the far. Pitch is in degrees; negative looks down. */
struct FZoomRange
{
	float NearArm = 1500.f;
	float FarArm = 12000.f;
	float NearPitch = -45.f;
	float FarPitch = -75.f;
};

/** Pure helpers for the overhead camera, kept apart from the actor so they can be tested. */
namespace CameraMath
{
	MURABITO_API float ArmLength(const FZoomRange& Range, float Zoom01);

	/** Tilt follows zoom: oblique when close, steep when far. */
	MURABITO_API float Pitch(const FZoomRange& Range, float Zoom01);

	MURABITO_API FVector2D ClampToBounds(const FVector2D& Point, const FBox2D& Bounds);

	/** (right, up-screen) -> world (X forward, Y right), for a camera at yaw 0. */
	MURABITO_API FVector2D ScreenDirToWorld(const FVector2D& ScreenDir);

	/** Mouse drag in pixels (screen coords, +Y down) -> world camera offset that keeps the ground under the cursor. */
	MURABITO_API FVector2D DragToWorld(const FVector2D& PixelDelta, float CmPerPixel);

	/** Pan speed in cm/s: BaseSpeed at the near limit, scaled by arm length. */
	MURABITO_API float PanSpeed(float BaseSpeed, const FZoomRange& Range, float Zoom01);
}
