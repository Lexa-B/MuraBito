#include "InputController.h"

#include "CameraMath.h"
#include "CameraRig.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "HexOverlay.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Terrain.h"

AInputController::AInputController()
{
	bShowMouseCursor = true;
	bEnableClickEvents = false;
	bEnableMouseOverEvents = false;
}

void AInputController::SetWorldRefs(ATerrain* InTerrain, AHexOverlay* InOverlay)
{
	Terrain = InTerrain;
	Overlay = InOverlay;
}

ACameraRig* AInputController::Rig() const
{
	return Cast<ACameraRig>(GetPawn());
}

void AInputController::CreateInputObjects()
{
	if (Context)
	{
		return;
	}
	MoveAction = NewObject<UInputAction>(this, TEXT("Move"));
	MoveAction->ValueType = EInputActionValueType::Axis2D;
	ZoomAction = NewObject<UInputAction>(this, TEXT("Zoom"));
	ZoomAction->ValueType = EInputActionValueType::Axis1D;

	Context = NewObject<UInputMappingContext>(this, TEXT("CameraControls"));

	// Move is (X right, Y up-screen). Keys give +X by default; Swizzle moves the value to Y; Negate flips it.
	auto MapMove = [this](const FKey& Key, bool bToY, bool bNegate)
	{
		FEnhancedActionKeyMapping& Mapping = Context->MapKey(MoveAction, Key);
		if (bToY)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(this)); // default order YXZ
		}
		if (bNegate)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(this));
		}
	};
	MapMove(EKeys::D, false, false);
	MapMove(EKeys::A, false, true);
	MapMove(EKeys::W, true, false);
	MapMove(EKeys::S, true, true);
	MapMove(EKeys::Right, false, false);
	MapMove(EKeys::Left, false, true);
	MapMove(EKeys::Up, true, false);
	MapMove(EKeys::Down, true, true);

	Context->MapKey(ZoomAction, EKeys::MouseWheelAxis);
}

void AInputController::SetupInputComponent()
{
	Super::SetupInputComponent();
	CreateInputObjects();

	UEnhancedInputComponent* Input = CastChecked<UEnhancedInputComponent>(InputComponent);
	Input->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AInputController::OnMove);
	Input->BindAction(ZoomAction, ETriggerEvent::Triggered, this, &AInputController::OnZoom);
}

void AInputController::BeginPlay()
{
	Super::BeginPlay();
	CreateInputObjects();
	if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		Subsystem->AddMappingContext(Context, 0);
	}

	FInputModeGameAndUI Mode;
	Mode.SetHideCursorDuringCapture(false);
	Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	SetInputMode(Mode);
}

void AInputController::OnMove(const FInputActionValue& Value)
{
	if (ACameraRig* R = Rig())
	{
		R->AddPan(Value.Get<FVector2D>());
	}
}

void AInputController::OnZoom(const FInputActionValue& Value)
{
	if (ACameraRig* R = Rig())
	{
		// Wheel up is positive and should zoom in.
		R->AddZoom(-Value.Get<float>());
	}
}

void AInputController::PlayerTick(float DeltaTime)
{
	Super::PlayerTick(DeltaTime);
	UpdateEdgeScroll();
	UpdateDrag();
	UpdateHover();
}

void AInputController::UpdateEdgeScroll()
{
	ACameraRig* R = Rig();
	float MouseX, MouseY;
	if (!R || bDragging || !GetMousePosition(MouseX, MouseY))
	{
		return;
	}
	int32 SizeX, SizeY;
	GetViewportSize(SizeX, SizeY);
	FVector2D Dir = FVector2D::ZeroVector;
	if (MouseX <= EdgeScrollMargin) Dir.X -= 1.0;
	if (MouseX >= SizeX - 1 - EdgeScrollMargin) Dir.X += 1.0;
	if (MouseY <= EdgeScrollMargin) Dir.Y += 1.0;
	if (MouseY >= SizeY - 1 - EdgeScrollMargin) Dir.Y -= 1.0;
	if (!Dir.IsZero())
	{
		R->AddPan(Dir);
	}
}

void AInputController::UpdateDrag()
{
	ACameraRig* R = Rig();
	float MouseX, MouseY;
	const bool bHaveMouse = GetMousePosition(MouseX, MouseY);
	const bool bDown = IsInputKeyDown(EKeys::MiddleMouseButton);
	if (!R || !bHaveMouse || !bDown)
	{
		bDragging = false;
		return;
	}
	const FVector2D Mouse(MouseX, MouseY);
	if (bDragging)
	{
		const float CmPerPixel = DragCmPerPixelPerArm * R->GetArmLength();
		R->AddPanWorld(CameraMath::DragToWorld(Mouse - LastMouse, CmPerPixel));
	}
	bDragging = true;
	LastMouse = Mouse;
}

void AInputController::UpdateHover()
{
	if (!Overlay.IsValid())
	{
		return;
	}
	TOptional<FHex> Tile;
	FHitResult Hit;
	if (Terrain.IsValid() && GetHitResultUnderCursor(ECC_Visibility, false, Hit) && Hit.GetActor() == Terrain.Get())
	{
		const FHexGrid& Grid = Overlay->GetGrid();
		const FHex Hex = Grid.XYToHex(FVector2D(Hit.ImpactPoint));
		if (Grid.Contains(Hex))
		{
			Tile = Hex;
		}
	}
	Overlay->SetHover(Tile);
}
